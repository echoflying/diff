import streamlit as st
from zhipuai import ZhipuAI
import openai
from volcenginesdkarkruntime import Ark


# zhipuai: glm-4-plus、glm-4-0520、glm-4 、glm-4-air、glm-4-airx、glm-4-long 、 glm-4-flashx 、 glm-4-flash
# kimi: 
# ark: 
# claude: 

class LLM_ai:
    _MODELS = {
        "zhipuai": {"url": "",   # SDK use default
                    "model": "glm-4-flash",
                    "key": "zhipuai-key",
                    "max_tokens": 8000,
                    },
        "kimi": {"url": "https://api-sg.moonshot.ai/v1",   # use openAI SDK
                    "model": "moonshot-v1-8k",
                    "key": "sk-kimi-key",
                    "max_tokens": 8000,
                    },
        "ark": {"url": "https://ark.cn-beijing.volces.com/api/v3",    # 火山方舟大模型，抖音，豆包，扣子是一家
                    "model": "ep-20240929221043-jsbgc",
                    "key": "ark-key",
                    "max_tokens": 4000,
                    },
        "claude": {"url": "https://api.gptapi.us/v1/chat/completions",       # Legend's testing bed
                    "model": "claude-3-5-sonnet",
                    "key": "sk-claud-key",
                    "max_tokens": 8000,
                    },
    }
    _llm = None
    _client = None

    
    def __init__(self, llm: str, model=""):
        self._llm = llm
        self._MODELS[llm]["key"] = st.secrets.ai_keys[llm]

        if llm == "zhipuai":
            self._client = ZhipuAI(api_key=self._MODELS[llm]["key"])
        elif llm == "kimi":
            self._client = openai.OpenAI(api_key=self._MODELS[llm]["key"],
                                         base_url = self._MODELS[llm]["url"])
        elif llm == "ark":
            self._client = Ark(api_key=self._MODELS[llm]["key"],
                               base_url=self._MODELS[llm]["url"])
        elif llm == "claude":
            self._client = openai.OpenAI(api_key=self._MODELS[llm]["key"], 
                                         base_url=self._MODELS[llm]["url"])
        else:
            raise ValueError(f"Invalid llm: {llm}")

        if not model == "":
            self._MODELS[llm]["model"] = model

    # use stream model if pass_chunk is not None
    def chat(self, prompt: str, t: str, pass_chunk= None):
        if pass_chunk is None:
            response = self._client.chat.completions.create(
                model=self._MODELS[self._llm]["model"],
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": t}
                ],
                temperature = 0.3,
            )
            return response.choices[0].message.content
        else:
            response = self._client.chat.completions.create(
                model=self._MODELS[self._llm]["model"],
                messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": t},
            ],
            temperature=0.3,
            stream=True,
            max_tokens=self._MODELS[self._llm]["max_tokens"],
            )

            answer=""
            for chunk in response:
                if chunk.choices[0].finish_reason is None:
                    print(vars(chunk),"\n\n")
                    pass_chunk(chunk.choices[0].delta.content)
                    answer = answer + chunk.choices[0].delta.content
                else:
                    break
            return answer
# end of class LLM_ai
