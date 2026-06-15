import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timezone

import requests


class AliyunClient:
    """阿里云服务客户端（纯 HTTP + V3 签名）"""

    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str = "cn-hangzhou"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region_id = region_id

        # 短信服务域名
        self.endpoint = "dysmsapi.aliyuncs.com"
        # API 版本
        self.api_version = "2017-05-25"
        # 签名算法
        self.algorithm = "ACS3-HMAC-SHA256"

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_hashed_payload(self, body: str) -> str:
        """计算请求体的 SHA256 哈希值（小写十六进制）"""
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _get_canonical_headers(self, headers: dict) -> tuple[str, str]:
        """构造规范化请求头，返回 (CanonicalHeaders, SignedHeaders)"""
        # 必须包含 host 和 x-acs-* 头
        canonical_headers = ""
        signed_headers = ""
        for key in sorted(headers.keys(), key=lambda x: x.lower()):
            lower_key = key.lower()
            value = headers[key].strip()
            canonical_headers += f"{lower_key}:{value}\n"
            if signed_headers:
                signed_headers += ";"
            signed_headers += lower_key
        return canonical_headers, signed_headers

    def _build_authorization(
        self,
        method: str,
        canonical_uri: str,
        canonical_query_string: str,
        headers: dict,
        body: str,
    ) -> str:
        # 1. 构建规范化请求
        canonical_headers, signed_headers = self._get_canonical_headers(headers)
        hashed_payload = self._get_hashed_payload(body)

        canonical_request = (
            f"{method.upper()}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_payload}"
        )

        # 2. 构建待签字符串
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = f"{self.algorithm}\n{hashed_canonical_request}"

        # 3. 计算签名
        signature = hmac.new(
            self.access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # 4. 构造 Authorization 头
        return (
            f"{self.algorithm} "
            f"Credential={self.access_key_id},"
            f"SignedHeaders={signed_headers},"
            f"Signature={signature}"
        )

    def _build_canonical_query_string(self, params: dict) -> str:
        """按参数名升序排列，构造规范化查询字符串"""
        encoded = {
            urllib.parse.quote(k, safe=""): urllib.parse.quote(str(v), safe="")
            for k, v in params.items()
        }
        return "&".join(f"{k}={v}" for k, v in sorted(encoded.items()))

    def _request(self, action: str, params: dict, endpoint: str = None, api_version: str = None) -> dict:
        """发送阿里云 RPC 风格 OpenAPI 请求（参数通过查询字符串传递）"""
        endpoint = endpoint or self.endpoint
        api_version = api_version or self.api_version

        # 请求时间（UTC）
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # RPC 风格：body 为空，参数放查询字符串
        body = ""
        canonical_query_string = self._build_canonical_query_string(params)

        # 请求头
        headers = {
            "host": endpoint,
            "x-acs-action": action,
            "x-acs-version": api_version,
            "x-acs-date": timestamp,
            "x-acs-signature-nonce": hashlib.md5(
                timestamp.encode("utf-8")
            ).hexdigest(),
            "x-acs-content-sha256": self._get_hashed_payload(body),
        }

        # 生成签名
        headers["authorization"] = self._build_authorization(
            method="POST",
            canonical_uri="/",
            canonical_query_string=canonical_query_string,
            headers=headers,
            body=body,
        )

        # 发送请求
        url = f"https://{endpoint}/?" + canonical_query_string
        response = requests.post(url, headers=headers)
        if not response.text:
            raise ValueError(
                f"阿里云 API 返回空响应，HTTP 状态码: {response.status_code}"
            )
        return response.json()

    def send_sms(
        self,
        phone_numbers: str,
        sign_name: str,
        template_code: str,
        template_param: dict = None,
    ) -> dict:
        """
        发送短信
        :param phone_numbers: 手机号码，多个用逗号分隔
        :param sign_name: 短信签名
        :param template_code: 短信模板 CODE
        :param template_param: 模板变量字典，例如 {"code":"1234"}
        :return: API 返回的 JSON
        """
        params = {
            "PhoneNumbers": phone_numbers,
            "SignName": sign_name,
            "TemplateCode": template_code,
        }
        if template_param:
            params["TemplateParam"] = json.dumps(template_param)
        return self._request("SendSms", params)

    def send_email(
        self,
        account_name: str,
        to_address: str,
        subject: str,
        html_body: str = None,
        text_body: str = None,
        reply_to_address: bool = False,
    ) -> dict:
        """
        发送单条邮件（阿里云邮件推送 DirectMail）
        :param account_name: 发信地址（控制台配置的发信账号）
        :param to_address: 收件人邮箱地址
        :param subject: 邮件主题
        :param html_body: HTML 格式邮件正文（与 text_body 二选一）
        :param text_body: 纯文本格式邮件正文（与 html_body 二选一）
        :param reply_to_address: 是否使用发信账号的回信地址，默认 False
        :return: API 返回的 JSON
        """
        if not html_body and not text_body:
            raise ValueError("html_body 和 text_body 至少提供一个")
        params = {
            "AccountName": account_name,
            "AddressType": 1,
            "ReplyToAddress": "true" if reply_to_address else "false",
            "ToAddress": to_address,
            "Subject": subject,
        }
        if html_body:
            params["HtmlBody"] = html_body
        else:
            params["TextBody"] = text_body
        return self._request(
            "SingleSendMail",
            params,
            endpoint="dm.aliyuncs.com",
            api_version="2015-11-23",
        )

