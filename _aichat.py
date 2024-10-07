import streamlit as st
from zhipuai import ZhipuAI
import openai
from volcenginesdkarkruntime import Ark


# zhipuai: glm-4-plus、glm-4-0520、glm-4 、glm-4-air、glm-4-airx、glm-4-long 、 glm-4-flashx 、 glm-4-flash
# kimi: 
# ark: 
# claude: 

# model info: model name, max tokens, llm name
class AI_models:
    _MODEL = {
        "glm-4-flash": {"llm": "zhipuai",   
                    "model": "glm-4-flash",
                    "max_tokens": 8000,
                    },
        "glm-4-5020": {"llm": "zhipuai",   
                    "model": "glm-4-5020",
                    "max_tokens": 8000,
                    },
        "kimi8k": {"llm": "kimi",   # use openAI SDK
                    "model": "moonshot-v1-8k",
                    "max_tokens": 8000,
                    },
        "doubao4": {"llm": "ark",    # 火山方舟大模型，抖音，豆包，扣子是一家
                    "model": "ep-20241005223718-nl742",    # Doubao-pro-4k
                    "max_tokens": 4000,
                    },
        "doubao32": {"llm": "ark",
                    "model": "ep-20240929221043-jsbgc",    # Doubao-pro-32k
                    "max_tokens": 4000,
                    },
        "claude35": {"llm": "claude",       # Legend's testing bed
                    "model": "claude-3-5-sonnet",
                    "max_tokens": 8000,
                    },
    }

    _working_model = {
        "llm" : "",
        "model" : "",
        "max_tokens" : 0
    }

    # nickname 1) key used in _MODEL; 2)llm.model.9999 for dedicated llm-model, bad format will raise runtime
    def __init__(self, model_nickname: str):
        if model_nickname in self._MODEL:
            self._working_model = self._MODEL[model_nickname]
        else:
            llm, model, n = model_nickname.split('.')
            self._working_model = {
                "llm" : llm,
                "model" : model,
                "max_tokens" : int(n)
            }

    def __getattr__(self, attr:str):
        return self._working_model[attr]


# maintain llm-url, get api-key, issue chat
class LLM_ai:

    _LLM = {
        "zhipuai": {"url": "",   # SDK use default
                    },
        "kimi": {"url": "https://api-sg.moonshot.ai/v1",   # use openAI SDK
                    },
        "ark": {"url": "https://ark.cn-beijing.volces.com/api/v3",    # 火山方舟大模型，抖音，豆包，扣子是一家
                    },
        "claude": {"url": "https://api.gptapi.us/v1/chat/completions",       # Legend's testing bed
                    },
    }

    # working one
    _llm = None
    _model = None
    _max_tokens = None
    _client = None

    
    def __init__(self, llm: str, model="", max_tokens= 2000):
        self._llm = llm
        ai_key = st.secrets.ai_keys[llm]

        if llm == "zhipuai":
            self._client = ZhipuAI(api_key=ai_key)    # zhipuai SDK use default url
        elif llm == "kimi":
            self._client = openai.OpenAI(api_key=ai_key, base_url = self._LLM[llm]["url"])
        elif llm == "ark":
            self._client = Ark(api_key=ai_key, base_url=self._LLM[llm]["url"])
        elif llm == "claude":
            self._client = openai.OpenAI(api_key=ai_key, base_url=self._LLM[llm]["url"])
        else:
            raise ValueError(f"Invalid llm: {llm}")

        if not model == "":
            self._model = model
        self._max_tokens = max_tokens

    # use stream model if pass_chunk is not None
    def chat(self, prompt: str, t: str, pass_chunk= None):
        if pass_chunk is None:
            response = self._client.chat.completions.create(
                model = self._model,
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": t}
                ],
                temperature = 0.3,
                max_tokens=self._max_tokens,
            )
            return response.choices[0].message.content
        else:
            response = self._client.chat.completions.create(
                model = self._model,
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": t},
                ],
                temperature=0.3,
                stream=True,
                max_tokens=self._max_tokens,
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
