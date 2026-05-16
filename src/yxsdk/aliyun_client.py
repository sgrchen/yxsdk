import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timezone

import requests


class AliyunSMSClient:
    """阿里云短信服务客户端（纯 HTTP + V3 签名）"""

    def __init__(self, access_key_id: str, access_key_secret: str, region_id: str = "cn-hangzhou"):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region_id = region_id

        # 短信服务域名
        self.endpoint = "dysmsapi.aliyuncs.com"
        # API 版本
        self.api_version = "2017-05-25"
        # 签名算法
        self.algorithm = "HMAC-SHA256"

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

        # 3. 计算签名密钥
        secret = self.access_key_secret + "&"
        signature = hmac.new(
            secret.encode("utf-8"),
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

    def _request(self, action: str, params: dict) -> dict:
        """发送阿里云 OpenAPI 请求"""
        # 请求时间（UTC）
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 请求头
        headers = {
            "host": self.endpoint,
            "x-acs-action": action,
            "x-acs-version": self.api_version,
            "x-acs-date": timestamp,
            "x-acs-signature-nonce": hashlib.md5(
                timestamp.encode("utf-8")
            ).hexdigest(),  # 简单生成唯一值
            "content-type": "application/json; charset=utf-8",
        }

        # 请求体
        body = json.dumps(params)

        # 生成签名
        headers["authorization"] = self._build_authorization(
            method="POST",
            canonical_uri="/",
            canonical_query_string="",  # 查询参数为空
            headers=headers,
            body=body,
        )

        # 发送请求
        url = f"https://{self.endpoint}/"
        response = requests.post(url, headers=headers, data=body.encode("utf-8"))
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

