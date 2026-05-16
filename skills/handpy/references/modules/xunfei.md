# 讯飞语音 xunfei

`xunfei.py` 通过 WebSocket 调用讯飞开放平台语音服务，需要讯飞开放平台 `APPID`、`APIKey`、`APISecret`，并且板子已联网。

接口已在板载文件导出和固件源码中分别核对过，`v2` 与 `v3` 的主接口一致。

## 导入

```python
from xunfei import Xunfei_speech, MODE_IAT, MODE_TTS
```

## 常量

| 常量 | 说明 |
|------|------|
| `MODE_IAT` | 语音识别（speech-to-text） |
| `MODE_TTS` | 语音合成（text-to-speech） |

## 构造函数

```python
Xunfei_speech(APPID, APIKey, APISecret, mode, AudioFile='', Text='')
```

参数说明：

| 参数 | 说明 |
|------|------|
| `APPID` | 讯飞应用 ID |
| `APIKey` | 讯飞 API Key |
| `APISecret` | 讯飞 API Secret |
| `mode` | `MODE_IAT` 或 `MODE_TTS` |
| `AudioFile` | 音频输入或输出文件路径 |
| `Text` | TTS 文本；源码按字节做 base64，建议传 `text.encode()` |

## 语音识别 IAT

```python
from xunfei import Xunfei_speech, MODE_IAT

speech = Xunfei_speech(
    APPID='your_appid',
    APIKey='your_api_key',
    APISecret='your_api_secret',
    mode=MODE_IAT,
    AudioFile='record.pcm'
)

text = speech.iat()
print(text)
```

注意：

- 识别时发送的是 `audio/L16;rate=8000` 的原始音频帧
- `iat()` 返回识别后的字符串

## 语音合成 TTS

```python
from xunfei import Xunfei_speech, MODE_TTS

speech = Xunfei_speech(
    APPID='your_appid',
    APIKey='your_api_key',
    APISecret='your_api_secret',
    mode=MODE_TTS,
    AudioFile='tts.pcm',
    Text='你好，掌控板'.encode()
)

speech.tts()
```

注意：

- TTS 业务参数使用 `audio/L16;rate=16000`
- `tts()` 会把合成结果写到 `AudioFile`
- `Text` 建议显式转成字节串传入

## 常用方法

| 方法 | 说明 |
|------|------|
| `iat()` | 执行语音识别并返回文本 |
| `tts()` | 执行语音合成并写出音频文件 |
| `create_url()` | 生成鉴权 URL / path，通常不需要手动调用 |

> 使用前需在讯飞开放平台申请 AppID、APIKey、APISecret。
> 需要 WiFi 连接。
> 鉴权依赖设备时间；若网络或时间异常，WebSocket 鉴权可能失败。
