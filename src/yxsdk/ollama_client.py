import requests
import json
import re

class OllamaClient:
    def __init__(self, model=None, base_url="http://localhost:11434", key=None):
        self.base_url = base_url
        self.model = model
        self.key = key
    
    def chat(self, messages, stream=False, model=None):
        url = f"{self.base_url}/api/chat"
        
        # 使用传入的model参数，如果没有则使用实例的model
        used_model = model or self.model
        if not used_model:
            raise ValueError("未指定模型名称")
        
        payload = {
            "model": used_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": 0.0
            }
        }
        
        try:
            response = requests.post(url, json=payload, stream=stream)
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def generate(self, prompt, stream=False, system=None, model=None, temperature=0.7, 
                 max_tokens=None, top_p=None, top_k=None, repeat_penalty=None, 
                 stop=None, context=None, raw=False):
        """使用 /api/generate 端点进行单次文本生成"""
        url = f"{self.base_url}/api/generate"
        
        # 使用传入的model参数，如果没有则使用实例的model
        used_model = model or self.model
        if not used_model:
            raise ValueError("未指定模型名称")
        
        payload = {
            "model": used_model,
            "prompt": prompt,
            "stream": stream,
            "think": False,
            "raw": raw  # 是否返回原始响应，不进行任何格式化
        }
        
        # 构建 options 参数
        options = {"temperature": temperature, "think": False}
        
        if max_tokens is not None:
            options["num_predict"] = max_tokens  # 最大生成token数
            
        if top_p is not None:
            options["top_p"] = top_p  # nucleus sampling参数
            
        if top_k is not None:
            options["top_k"] = top_k  # top-k sampling参数
            
        if repeat_penalty is not None:
            options["repeat_penalty"] = repeat_penalty  # 重复惩罚
            
        if stop is not None:
            options["stop"] = stop if isinstance(stop, list) else [stop]  # 停止词
            
        payload["options"] = options
        
        # 如果提供了系统提示，添加到payload中
        if system:
            payload["system"] = system
            
        # 如果提供了上下文，添加到payload中
        if context is not None:
            payload["context"] = context
        
        try:
            headers = {}
            if self.key:
                headers['Authorization'] = f"Bearer {self.key}"
            response = requests.post(url, headers=headers, json=payload, stream=stream)
            response.raise_for_status()
            
            if stream:
                return self._handle_generate_stream_response(response)
            else:
                content = response.json()
                if 'response' in content:
                    return content['response']
                else:
                    print("响应格式错误，未找到 'response' 字段")
                    return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def embed_text(self, text, model=None):
        """对单个文本进行嵌入向量化"""
        url = f"{self.base_url}/api/embeddings"
        
        # 使用传入的model参数，如果没有则使用实例的model
        used_model = model or self.model
        if not used_model:
            raise ValueError("未指定模型名称")
        
        payload = {
            "model": used_model,
            "prompt": text
        }
        
        try:
            headers = {}
            if self.key:
                headers['Authorization'] = f"Bearer {self.key}"
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            content = response.json()
            if 'embedding' in content:
                return content['embedding']
            else:
                print("响应格式错误，未找到 'embedding' 字段")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
    
    def embed_documents(self, documents, model=None):
        """对多个文档进行批量嵌入向量化
        
        Args:
            documents: 文档列表，可以是字符串列表
            model: 模型名称
            
        Returns:
            list: 嵌入向量列表，每个元素对应一个文档的嵌入向量
        """
        if not isinstance(documents, list):
            raise ValueError("documents 参数必须是列表")
        
        embeddings = []
        for i, doc in enumerate(documents):
            try:
                embedding = self.embed_text(doc, model)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    print(f"文档 {i+1} 嵌入失败")
                    embeddings.append(None)
            except Exception as e:
                print(f"处理文档 {i+1} 时出错: {e}")
                embeddings.append(None)
        
        return embeddings
    
    def _handle_stream_response(self, response):
        """处理流式响应"""
        for line in response.iter_lines():
            if line:
                try:
                    # 解码字节为字符串
                    if isinstance(line, bytes):
                        line = line.decode('utf-8')
                    
                    # 移除可能的 "data: " 前缀
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    data = json.loads(line)
                    if 'message' in data and 'content' in data['message']:
                        content = data['message']['content']
                        if content:  # 只返回非空内容
                            yield content
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"解析响应错误: {e}")
                    continue
    
    def _handle_generate_stream_response(self, response):
        """处理 generate 端点的流式响应，支持思考模型的 <thinking> 标签输出"""
        in_thinking = False

        for line in response.iter_lines():
            if not line:
                continue
            try:
                if isinstance(line, bytes):
                    line = line.decode('utf-8')

                if line.startswith('data: '):
                    line = line[6:]

                data = json.loads(line)

                thinking_content = data.get('thinking', '')
                response_content = data.get('response', '')

                if thinking_content:
                    if not in_thinking:
                        yield "<thinking>\n"
                        in_thinking = True
                    yield thinking_content
                elif in_thinking:
                    # thinking 字段变空，代表思考阶段结束
                    yield "</thinking>\n"
                    in_thinking = False

                if response_content:
                    yield response_content

            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"解析响应错误: {e}")
                continue

        # 确保流异常结束时 thinking 标签正确闭合
        if in_thinking:
            yield "</thinking>\n"

