from abc import ABC, abstractmethod
import importlib

class ProtocolConverterInterface(ABC):
    @abstractmethod
    def convert(self, message):
        pass

    @abstractmethod
    def get_input_protocol(self):
        pass

    @abstractmethod
    def get_output_protocol(self):
        pass

class ProtocolConverterManager:
    def __init__(self):
         self.protocol_converters = {}
    
    def load_converters(self, converter_names):
        for name in converter_names:
            try:
                module = importlib.import_module(name)
                converter_class = getattr(module, 'ProtocolConverter')
                converter = converter_class()
                input_protocol = converter.get_input_protocol()
                output_protocol = converter.get_output_protocol()
                key = (input_protocol, output_protocol)
                self.protocol_converters[key] = converter
            except Exception as e:
                print(f"加载协议转换器 {name} 失败: {e}")
    
    def get_converter(self, input_protocol, output_protocol):
        key = (input_protocol, output_protocol)
        return self.protocol_converters.get(key)
    