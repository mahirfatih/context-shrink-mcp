# Context Shrink

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/MCP-stdio-lightgrey)
![Client](https://img.shields.io/badge/client-OpenCode-green)
![License](https://img.shields.io/badge/license-MIT-blue)

🌐 [English](./README.md) · **Türkçe**

**Context Shrink**, **OpenAI uyumlu herhangi bir uç noktaya** giden istekleri modelin bağlam (context) sınırının altında tutan küçük bir MCP sunucusudur. Çağrıdan önce bağlamı ölçer, ardından en eski mesajları ya **atar** ya da bir özete **sıkıştırır** — böylece sunucunun isteği reddetmesinin önüne geçer. Şunlarla çalışır (örnek):

- oMLX
- llama.cpp (`llama-server`)
- LM Studio
- vLLM
- OpenAI API'si
- OpenAI uyumlu herhangi bir ağ geçidi

Tam liste için [Uyumlu altyapılar](#-uyumlu-altyapılar) bölümüne bakın.

> **Token sayımı:** kuruluysa yakın bir tahmin için `tiktoken` kullanır (varsayılan `cl100k_base`), aksi hâlde tokenizer'sız bir tahmine (karakter sayısı ÷ 4) düşer. Her iki durumda da bu bir güvenlik bariyeridir, kesin bir bütçe değildir — davranışı değiştirmek için `CONTEXT_SHRINK_TOKENIZER` (veya eski `OMLX_SHRINK_*` / `OPENAI_SHRINK_*` adları) ayarlanır.

---

## 🔌 Uyumlu altyapılar

Sunucu yalnızca bir **OpenAI uyumlu `/v1/chat/completions` uç noktası** ister —
yerel model sunucuları, kendi GPU'unuzda çalışan motorlar ve OpenAI ağ geçitleri
hepsi uyar. `CONTEXT_SHRINK_BASE_URL` ve `CONTEXT_SHRINK_MODEL` ile yönlendirin.
Tel protokolü, başlıklar ve hata biçimleri
[`OPENAI-API-REFERENCE.md`](./OPENAI-API-REFERENCE.md) dosyasında özetlenmiştir.

### En yaygın olanlar için hızlı yapılandırma

| Altyapı | Base URL | Model değeri | Notlar |
| :--- | :--- | :--- | :--- |
| oMLX | `http://127.0.0.1:8000/v1` | *(varsayılan)* | Orijinal hedef |
| Ollama | `http://127.0.0.1:11434/v1` | örn. `qwen2.5-coder` | API anahtarı gerektirmez |
| llama.cpp (`llama-server`) | `http://127.0.0.1:8080/v1` | GGUF adınız | CPU/GPU, hafif |
| LM Studio | `http://127.0.0.1:1234/v1` | yüklenen model id'si | Kısayol gerekmez |
| vLLM | `http://127.0.0.1:8000/v1` | sunulan model id'si | Üretim için, PagedAttention |
| Text Generation Inference (TGI) | `http://127.0.0.1:8080/v1` | sunulan model id'si | HuggingFace, streaming |
| SGLang | `http://127.0.0.1:30000/v1` | sunulan model id'si | Yüksek verim |
| LocalAI | `http://127.0.0.1:8080/v1` | model adı | Drop-in replacement |
| OpenAI / ağ geçidi | `https://api.openai.com/v1` | örn. `gpt-4o-mini` | API anahtarı verin |

Ollama örneği:

```bash
export CONTEXT_SHRINK_BASE_URL="http://127.0.0.1:11434/v1"
export CONTEXT_SHRINK_MODEL="qwen2.5-coder"
```

### ☁️ Uzak / bulut OpenAI-uyumlu sağlayıcılar

Yerel tek seçenek değil: büyük sağlayıcıların hepsi OpenAI uyumlu bir
`/v1/chat/completions` uç noktası sunar. Sunucuyu ona yöneltin ve
`CONTEXT_SHRINK_API_KEY` verin. Hepsi bir anahtar ya da token ister.

- **OpenAI**
  - Base URL: https://api.openai.com/v1
  - Model: gpt-4o-mini
- **Azure OpenAI**
  - Base URL: https://{resource}.openai.azure.com/openai/deployments/{deployment}
  - Model: deployment adınız
  - `Authorization` yerine `api-key` başlığı kullanır — aşağıya bakın
- **DeepSeek**
  - Base URL: https://api.deepseek.com/v1
  - Model: deepseek-chat
- **Groq**
  - Base URL: https://api.groq.com/openai/v1
  - Model: llama-3.3-70b-versatile
  - Çok hızlı
- **Together AI**
  - Base URL: https://api.together.xyz/v1
  - Model: meta-llama/Llama-3.3-70B-Instruct-Turbo
- **Fireworks AI**
  - Base URL: https://api.fireworks.ai/inference/v1
  - Model: accounts/fireworks/models/llama-v3p3-70b-instruct
- **Mistral API**
  - Base URL: https://api.mistral.ai/v1
  - Model: mistral-large-latest
- **OpenRouter**
  - Base URL: https://openrouter.ai/api/v1
  - Model: model slug'ı
  - 200+ modele yönlendirir
- **HuggingFace Inference Endpoints**
  - Base URL: https://{endpoint'iniz}/v1
  - Model: modeliniz
  - Özel uç nokta
- **Cloudflare Workers AI**
  - Base URL: https://api.cloudflare.com/client/v4/accounts/{account-id}/ai/v1
  - Model: @cf/meta/llama-3.3-70b-instruct-fp8

Azure OpenAI bearer `Authorization` başlığı kullanmaz; gizli anahtarı özel
başlık olarak geçirin:

```bash
export CONTEXT_SHRINK_BASE_URL="https://myresource.openai.azure.com/openai/deployments/my-deployment"
export CONTEXT_SHRINK_MODEL="my-deployment"
export CONTEXT_SHRINK_EXTRA_HEADERS='{"api-key": "azure-secret"}'
```

Herhangi bir ağ geçidi için ek statik başlıklar `CONTEXT_SHRINK_EXTRA_HEADERS`
ile JSON nesnesi biçiminde kabul edilir (örneğin org id ya da özel yönlendirme
başlığı).

### Tam katalog

Aşağıdakilerin hepsi özetleme uç noktası olarak kullanılabilir; listelenmeyen
OpenAI uyumlu uç noktalar da çalışır.

- **Yerel model sunucuları:**
  - Ollama
  - llama.cpp (`llama-server`)
  - LM Studio
  - Jan
  - GPT4All (Python API)
  - llamafile (`--server`)
  - KoboldCpp
  - Oobabooga Text Generation WebUI (OpenAI eklentisi)
  - MLC LLM
  - Petals (dağıtık)
- **GPU / üretim motorları:**
  - vLLM
  - Aphrodite Engine (vLLM fork'u)
  - Text Generation Inference (TGI)
  - SGLang
  - NVIDIA NIM / TensorRT-LLM
  - ExLlamaV2 + TabbyAPI
  - Xinference
  - OpenLLM (BentoML)
  - FastChat (LMSYS)
  - LocalAI
- **Proxy'ler ve router'lar:**
  - LiteLLM (100+ sağlayıcı)
  - OpenRouter
  - Portkey Gateway
  - One API / New API
  - topluluk Ollama-to-OpenAI proxy'leri
- **Kütüphaneler / özel yapılar:**
  - `llama-cpp-python` (`llama_cpp.server`)
  - Transformers + FastAPI
  - AnythingLLM / Msty

---

## 📖 Genel Bakış

Bu sınıftaki modeller için oMLX profilleri **32K bağlam** (`max_context_window: 32768`) ile çalışır. Bu bilinçli bir tercihtir: 4-bit KV önbelleğiyle çalışma zamanı ayak izini model başına yaklaşık 17–20 GB'ta tutar ve Apple Silicon'da prefill'i kısa tutar. Sınırı yükseltmek bedavadır değildir — bağlamdaki her ek token, bellekte ve prefill süresinde ödenir.

Maliyet uzun bir oturumda ortaya çıkar. Toplam tavanı aşana kadar üç şey büyümeye devam eder:

- sistem promptu
- konuşma geçmişi
- araç sonuçları

Tavanı aştığında sunucu tüm isteği reddeder:

```text
Prompt is too long: 39514 tokens > 32768 maximum context length
```

Bu noktada ajan durur. Soruda yanlış bir şey yoktu — prompt yalnızca 6.7K token fazlaydı. Alışılmış çözüm yollarının hiçbiri tatmin edici değildir:

| Çözüm yolu | Neden yetersiz |
| :--- | :--- |
| `max_context_window` değerini yükseltmek | Duvarı kaydırır, kaldırmaz; aynı makinede bellek ve prefill hızına mal olur |
| Elle kırpmak | Manuel, unutması kolay, koca oturumları çöpe atar |
| Yeni bir oturum başlatmak | Görevi çalıştıran bağlamı kaybeder |

Bu yüzden sunucu ucuz yolu seçer: **32K'yı koru, daha küçük bir prompt gönder.**

Tam anlatımı okuyun (neden 32K, üç sıkıştırma modu, ortam değişkenleri ve bilinen sınırlamalar):

**[English →](./README.md)** · **[Türkçe →](./README.tr.md)**

---

## ✅ Öneri

Sabit bir bağlam penceresine sahip oMLX veya başka bir yerel OpenAI-uyumlu sunucu kullanıyorsanız ve en az bir kez `Prompt is too long` hatası aldıysanız kullanın. Tek bir Python dosyasıdır ve GPU gerektirmez. `estimate_context` ve `trim_context` saf aritmetiktir — çıkarım zamanında hiçbir maliyeti yoktur. `compact_context` yalnızca özetlemesini istediğinizde yerel modeli çağırır (ya da hazır bir özet verirsiniz ve hiçbir şey çağırmaz).

Bağlam pencereniz oturumlarınız için yeterince büyükse ya da istemciniz geçmişi kendi başına sıkıştırıyorsa muhtemelen buna ihtiyacınız yok.

---

## 🛠️ Teknoloji Yığını ve Mimari

- **Dil ve Çalışma Zamanı:** Python 3.10+, yalnızca standart kütüphane
- **Protokol:** Model Context Protocol (MCP), stdio taşıması üzerinden
- **İstemci:** OpenCode (Code Mode araçları `tools.Context_Shrink.*` altında gruplar)
- **Sıkıştırma Motoru:** Yerel OpenAI-uyumlu endpoint üzerinden parçalı (chunked) özetleme
- **Token Sayımı:** opsiyonel `tiktoken` (varsayılan `cl100k_base`), karakter tabanlı heuristic fallback — zorunlu bağımlılık yok
- **Bağımlılıklar:** `mcp` (MCP SDK) zorunlu; `tiktoken` opsiyonel — GPU gerekmez
- **Hedef Sunucu:** OpenAI uyumlu herhangi bir sunucu — bkz. [Uyumlu altyapılar](#-uyumlu-altyapılar)
- **Varsayılanlar:** `max_context_tokens = 32768`, `keep_last = 8`, `threshold = 0.8`

---

## ✨ Özellikler

- 🧮 **Yeterince doğru tahmin** — `estimate_context` tahmini token sayısını, kalan bütçeyi ve `should_trim` bayrağını döner
- ✂️ **En eski mesajları at** — `trim_context`, en eski mesajları çıkarılmış mesaj listesini döner; en yeni `keep_last` tanesini korur
- 🧠 **Atmak yerine sıkıştır** — `compact_context`, en eski mesajları bir **özetle** değiştirir; baştaki sistem mesajlarını ve en yeni `keep_last` tanesini aynen korur
- 📝 **Üç sıkıştırma modu** — özet verilmiş, modelle üretilmiş veya yalnızca plan (`needs_summary: true`, mesaj içeriği geri döndürülmez)
- 🌐 **Opsiyonel gerçek tokenizer** — kuruluysa `tiktoken`, aksi hâlde tokenizer'sız tahmin (karakter ÷ 4); seçimi `CONTEXT_SHRINK_TOKENIZER` belirler
- 🔌 **Sade MCP** — herhangi bir MCP istemcisi sunucuyu kullanabilir, yalnızca OpenCode değil
- 🧩 **Parçalı özetleme** — uzun geçmişler parça parça özetlenir, böylece yerel model özetlerken taşmaz
- 🔒 **Telemetri yok, ağ çağrısı yok** — opsiyonel yerel özetleyici isteği hariç

---

## 📸 Ekran Görüntüleri

_(Arayüz yok — bu başsız (headless) bir MCP sunucusudur. Araç çıktısı stdio üzerinden JSON'dur.)_

---

## 🏗️ Mimari

```mermaid
flowchart LR
    classDef client fill:#e3f2fd,stroke:#1976d2,color:#0d47a1
    classDef decision fill:#fff3e0,stroke:#ef6c00,color:#e65100
    classDef action fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
    classDef model fill:#fce4ec,stroke:#c2185b,color:#880e4f

    Client["🧑‍💻 Kod ajanınız"]:::client
    Client -->|"her istekten önce"| Fits{"Bağlam penceresine<br/>sığıyor mu?"}:::decision

    Fits -->|"evet"| Model
    Fits -->|"hayır"| Choice{"Ne yapılmalı?"}:::decision

    Choice -->|"sadece ölç"| Measure["📊 Boyutu bildir<br/>hiçbir şey değişmez"]:::action
    Choice -->|"eskileri at"| Trim["✂️ Geçmişi kısalt<br/>en yeni mesajlar kalır"]:::action
    Choice -->|"özetle"| Compact["🗜️ En eski kısmı özetle<br/>son mesajlar birebir korunur"]:::action

    Trim --> Model
    Compact --> Model
    Model["🤖 Yerel model<br/>(oMLX)"]:::model
```

---

### `compact_context` üç modda

1. **Özet verilmiş** — `summary="..."` geçin, model çağrısı yapılmaz. Ajan (veya
   kullanıcı) özeti zaten yazdıysa bunu kullanın.
2. **Modelle üretilmiş** — `model="..."` (ve isteğe bağlı `base_url`) geçin ya da
   aşağıdaki ortam değişkenlerini ayarlayın; sunucu en eski mesajları sizin için
   özetler. Uzun geçmişler parça parça özetlenir, böylece yerel model özetlerken
   taşmaz.
3. **Yalnızca plan** — ikisi de yoksa çağrı `needs_summary: true`, kullanılacak tam
   `summary_prompt` ve token sayılarını döner. **Hiçbir mesaj içeriği geri
   döndürülmez**, bu yüzden sonuç küçük kalır; `summary=<metin>` ile tekrar
   çağırın. Ortam bir model tanımlasa bile bu adımı zorlamak için `model=""` geçin.

`compact_context` birleştirilmiş `messages` listesini yalnızca 1 ve 2. modlarda
döner ve tahmin `threshold` içindeyse, `force: true` geçmediğiniz sürece listeyi
değiştirmez (`compacted: false`).

> **Model endpoint'i gerekmez:** 1 ve 3. modlar hiçbir `CONTEXT_SHRINK_*` değişkeni
> olmadan çalışır. Ortam değişkenleri yalnızca 2. modu etkinleştirir.

---

## 🚀 Kurulum ve Hızlı Başlangıç

### 1. Gereksinimler

| Gereksinim | Sürüm / Notlar |
| :--- | :--- |
| **Python** | 3.10+ (`/opt/homebrew/bin/python3` ile test edildi) |
| **MCP SDK** | `pip install "mcp>=2.0"` |
| **Tokenizer** *(opsiyonel)* | Gerçek token sayımı için `pip install tiktoken`; aksi hâlde karakter ÷ 4'e düşer |
| **İstemci** | OpenCode (veya herhangi bir MCP istemcisi) |
| **Model sunucusu** | oMLX veya başka bir yerel OpenAI-uyumlu sunucu (opsiyonel, model modu için) |

### 2. SDK'yı kurun

```bash
pip install "mcp>=2.0"
```

### 3. Sunucuyu kopyalayın

`context-shrink.py` dosyasını seçtiğiniz bir dizine kopyalayın (örneğin `~/.config/opencode/mcp/`).

> **Not:** `command` dizisindeki `python3` beklediğiniz yorumlayıcı olmayabilir —
> kurulumunuza göre `/opt/homebrew/bin/python3`, `/usr/bin/python3` veya başka bir
> yer olabilir. Yolu `which python3` (veya `which python`) ile doğrulayın ve
> gerekirse düz `python3` yerine mutlak yolu kullanın.

### 4. OpenCode'a kaydedin

Sunucuyu OpenCode yapılandırmanıza (`~/.config/opencode/opencode.jsonc`) ekleyin:

```jsonc
{
  "mcp": {
    "servers": {
      "Context Shrink": {
        "type": "local",
        "command": [
          "python3",
          "/absolute/path/to/context-shrink.py"
        ],
        "timeout": 180000
      }
    }
  }
}
```

Yapılandırma değişiklikleri yeniden başlatma gerektirmez — OpenCode yapılandırma dosyalarını izler ve kayıttan sonra MCP sunucularını yeniden yükler. Tam yeniden yükleme için `/reload` çalıştırın.

### 5. (Opsiyonel) Model modunu etkinleştirin

`compact_context` yerel modelle özetleyebilsin diye ortam değişkenlerini MCP girdisindeki `environment` altında ayarlayın. Aşağıdaki değerler bu projenin geliştirildiği kurulumdur — Apple Silicon üzerinde yerel bir **oMLX** sunucusu, `Qwen3.6-35B-A3B-4bit` modelini sunar:

```jsonc
"environment": {
  "CONTEXT_SHRINK_MODEL": "Qwen3.6-35B-A3B-4bit",
  "CONTEXT_SHRINK_BASE_URL": "http://127.0.0.1:8000/v1",
  "CONTEXT_SHRINK_API_KEY": "omlx-...",
  "CONTEXT_SHRINK_TIMEOUT": "180",
  "CONTEXT_SHRINK_TOKENIZER": "auto"
}
```

### Gerçek kurulum (bu projenin geliştirme makinesi)

Bu sunucu, Apple Silicon bir Mac'te yerel bir **oMLX** sunucusuyla geliştirildi ve
her gün bu kurulumda kullanılıyor — hedeflediği 32K bağlam profili
[`mahirfatih/omlx-m1-max-benchmark`](https://github.com/mahirfatih/omlx-m1-max-benchmark)
deposunda belgelenmiştir. Oradaki OpenCode girdisi, sunucuyu özel bir sanal ortam
(virtualenv) üzerinden çalıştırır ve özetleyiciyi yerel modele yöneltir:

```jsonc
{
  "mcp": {
    "servers": {
      "Context Shrink": {
        "type": "local",
        "command": [
          "/absolute/path/to/context-shrink-venv/bin/python",
          "/absolute/path/to/context-shrink.py"
        ],
        "environment": {
          "CONTEXT_SHRINK_MODEL": "Qwen3.6-35B-A3B-4bit",
          "CONTEXT_SHRINK_BASE_URL": "http://127.0.0.1:8000/v1",
          "CONTEXT_SHRINK_API_KEY": "omlx-...",
          "CONTEXT_SHRINK_TOKENIZER": "auto"
        },
        "timeout": 180000
      }
    }
  }
}
```

> `CONTEXT_SHRINK_API_KEY`, yerel oMLX sunucusunun beklediği token'dır; burada
> sansürlenmiştir. Yolları ve anahtarı kendi değerlerinizle değiştirin.

### Yapılandırma

`compact_context`, argümanlar verilmediğinde endpoint'ini ve modelini ortamdan okur:

Kanonik adlar `CONTEXT_SHRINK_*`'tır. Eski `OMLX_SHRINK_*` adları ve
tedarikçi-tarafsız `OPENAI_SHRINK_*` diğer adları aynı anlama gelir ve yalnızca
daha yüksek öncelikli bir ad ayarlı değilse kullanılır. Öncelik:

```text
CONTEXT_SHRINK_*  >  OMLX_SHRINK_* (eski)  >  OPENAI_SHRINK_*
```

| Değişken | Varsayılan | Anlamı |
| :--- | :--- | :--- |
| `CONTEXT_SHRINK_BASE_URL` / `OMLX_SHRINK_BASE_URL` / `OPENAI_SHRINK_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-uyumlu base URL (sonunda `/chat/completions` olan da kabul edilir) |
| `CONTEXT_SHRINK_MODEL` / `OMLX_SHRINK_MODEL` / `OPENAI_SHRINK_MODEL` | *(boş)* | Özetleme için kullanılacak model adı; boşsa model modu kapalıdır |
| `CONTEXT_SHRINK_API_KEY` / `OMLX_SHRINK_API_KEY` / `OPENAI_SHRINK_API_KEY` | *(boş)* | Sunucu gerektiriyorsa Bearer token |
| `CONTEXT_SHRINK_TIMEOUT` / `OMLX_SHRINK_TIMEOUT` / `OPENAI_SHRINK_TIMEOUT` | `180` | Özetleyici istek zaman aşımı, saniye (geçersiz değer 180'e düşer) |
| `CONTEXT_SHRINK_TOKENIZER` / `OMLX_SHRINK_TOKENIZER` / `OPENAI_SHRINK_TOKENIZER` | `auto` | Token sayacı: `auto` (kuruluysa tiktoken `cl100k_base`, yoksa heuristic), bir tiktoken encoding adı veya her zaman karakter ÷ 4 için `heuristic`/`off` |
| `CONTEXT_SHRINK_MAX_CONTEXT_TOKENS` / `OMLX_SHRINK_MAX_CONTEXT_TOKENS` / `OPENAI_SHRINK_MAX_CONTEXT_TOKENS` | `32768` | Her araç çağrısı için varsayılan bağlam bütçesi |
| `CONTEXT_SHRINK_EXTRA_HEADERS` / `OMLX_SHRINK_EXTRA_HEADERS` / `OPENAI_SHRINK_EXTRA_HEADERS` | *(boş)* | Azure OpenAI gibi ağ geçitleri için ek HTTP başlıkları, JSON nesnesi biçiminde (`{"api-key": "..."}`) |
| `CONTEXT_SHRINK_LOG_LEVEL` / `OMLX_SHRINK_LOG_LEVEL` / `OPENAI_SHRINK_LOG_LEVEL` | `INFO` | stderr günlük seviyesi (sorun giderirken `DEBUG`); geçersiz ad `INFO`'ya düşer |

### Sık yapılan hatalar

- **Boş `CONTEXT_SHRINK_MODEL`** `compact_context`'i yalnızca plan moduna alır:
  model çağırmak yerine bir `needs_summary` planı döner.
- **Çok küçük `max_context_tokens`** her çağrıyı bütçe aşımı gibi gösterir; modele
  gerçek bağlam penceresini verin (varsayılan `32768`).
- **`*_EXTRA_HEADERS` bir JSON nesnesi olmalıdır** — string, dizi veya bozuk JSON
  uyarıyla birlikte yok sayılır.
- **Uzak/bulut `CONTEXT_SHRINK_BASE_URL`** mesajlarınızı o uç noktaya gönderir;
  yalnızca güvendiğiniz bir sunucuyu gösterin.
- Aralık dışı `max_context_tokens` değerleri `1…1000000` aralığına kırpılır, böylece
  bir yazım hatası belleği tüketemez.

### 6. Kullanın

- Geçerli mesaj listesiyle `estimate_context` çağırın.
- `should_trim` `true` ise, `trim_context` çağırıp dönen listeyi gönderin ya da
  atmak yerine özü korumak için `compact_context` kullanın.
- Bir ajan, tahmin sınırı aştığında bunu her istekten önce otomatik yapabilir.

Örnek `estimate_context` çağrısı:

```json
{
  "messages": [
    { "role": "user", "content": "ilk mesaj" },
    { "role": "assistant", "content": "ilk yanıt" },
    { "role": "user", "content": "ikinci mesaj" }
  ],
  "max_context_tokens": 32768
}
```

Örnek `trim_context` çağrısı:

```json
{
  "messages": [ "..." ],
  "keep_last": 8,
  "max_context_tokens": 32768
}
```

Sıkıştırma akışı, model modu:

```json
{
  "messages": [ "..." ],
  "keep_last": 8,
  "model": "Qwen3.6-35B-A3B-4bit",
  "base_url": "http://127.0.0.1:8000/v1"
}
```

Sıkıştırma akışı, ajan modu (iki çağrı):

1. `compact_context({ "messages": [...], "force": true })` → `needs_summary: true`
   ve `summary_prompt`.
2. Ajan özeti yazar, ardından tekrar çağırır:
   `{ "messages": [...], "force": true, "summary": "<o metin>" }` → sıkıştırılmış
   `messages` listesi.

### Araç parametreleri

| Araç | Parametre | Varsayılan | Anlamı |
| :--- | :--- | :--- | :--- |
| *(hepsi)* | `messages` | *(zorunlu)* | `role` / `content` çiftlerinden oluşan konuşma |
| `estimate_context` | `max_context_tokens` | `32768` | Tahminin karşılaştırılacağı bütçe |
| `trim_context` | `keep_last` | `8` | Her zaman korunan en yeni mesaj sayısı |
| `trim_context` | `max_context_tokens` | `32768` | Kırpılacak hedef bütçe |
| `compact_context` | `keep_last` | `8` | Aynen korunan en yeni mesaj sayısı |
| `compact_context` | `max_context_tokens` | `32768` | Bağlam bütçesi |
| `compact_context` | `threshold` | `0.8` | Bütçenin bu oranının üzerinde sıkıştır (aksi hâlde `force` gerekir) |
| `compact_context` | `force` | `false` | `threshold` altında olsa bile sıkıştır |
| `compact_context` | `summary` | *(yok)* | Hazır özet (mod 1) |
| `compact_context` | `model` | *(ortam)* | Üretilen özet için model (mod 2); `""` yalnızca plan adımını zorlar |
| `compact_context` | `base_url` | *(ortam)* | Özetleyici için uç nokta geçersiz kılma |
| `compact_context` | `api_key` | *(ortam)* | Özetleyici için Bearer token geçersiz kılma |
| `compact_context` | `summary_budget_tokens` | `512` | Üretilen özet için üst sınır |
| `compact_context` | `summary_role` | `"system"` | Özeti taşıyan mesajın rolü |

`estimate_context` ayrıca kullanılan sayacı belirten bir `tokenizer` alanı döner
(örneğin `tiktoken:cl100k_base` veya `heuristic(chars/4)`).

### Minimal Python istemci

[`examples/python-client.py`](./examples/python-client.py) çalıştırılabilir bir
istemcidir: sunucuyu stdio üzerinden başlatır, araçları listeler ve
`estimate_context` çağırır.

```bash
python examples/python-client.py                          # ./context-shrink.py kullanır
python examples/python-client.py /yol/context-shrink.py
```

`mcp` kurulu olan aynı yorumlayıcıyla çalıştırın.

---

## 📂 Proje Yapısı

```
context-shrink-mcp/
├── context-shrink.py        # Tek dosyalık MCP sunucusu (ürünün tamamı)
├── README.md                # İngilizce dokümantasyon
├── README.tr.md             # Bu dosya (Türkçe)
├── CONTRIBUTING.md          # Kurulum, testler, commit kuralları
├── CHANGELOG.md             # Keep a Changelog sürüm notları
├── OPENAI-API-REFERENCE.md  # Uç nokta, başlıklar ve hata biçimleri
├── requirements.txt         # Çalışma zamanı bağımlılığı (mcp)
├── requirements-dev.txt     # Geliştirme bağımlılıkları (mcp, pytest, ruff, tiktoken)
├── pytest.ini               # pytest yapılandırması (testpaths, python_files)
├── .ruff.toml               # Ruff lint yapılandırması
├── .pre-commit-config.yaml  # Opsiyonel yerel git hook'ları
├── .github/workflows/ci.yml # CI: lint + derleme + testler
├── test/                    # Test runner + pytest testleri
│   ├── test.sh              # Tek test runner (ruff + pytest)
│   ├── README.md            # Test klasörü kılavuzu
│   ├── context-shrink-tests.py # Saf yardımcılar + tokenizer çözümleme + fixture'lar
│   └── context-shrink-mcp-tests.py # STDIO uçtan uca tur
├── examples/                # Çalıştırılabilir örnekler
│   └── python-client.py     # Minimal MCP istemcisi: araçları listele + birini çağır
├── LICENSE                  # MIT
└── .gitignore
```

---

## 🧪 Test ve CI

```bash
./test/test.sh              # dev bağımlılıkları kur, sonra ruff + pytest
./test/test.sh --lint       # yalnızca ruff
./test/test.sh --no-install # pip install adımını atla
./test/test.sh --only test/context-shrink-tests.py::test_compact_uses_provided_summary
```

- **Runner:** [`test/test.sh`](./test/test.sh) geliştirme bağımlılıklarını kurar, Ruff ve ardından pytest çalıştırır. Yorumlayıcı, varsa proje `.venv`'i, yoksa `python3`'tür.
- **Paketler:** [`test/context-shrink-tests.py`](./test/context-shrink-tests.py) saf yardımcıları (token tahmini, kırpma, sıkıştırma bölme ve parçalama), tokenizer çözümleme mantığını ve ortam değişkeni ayrıştırmayı kapsar — ağ yok. [`test/context-shrink-mcp-tests.py`](./test/context-shrink-mcp-tests.py) ise gerçek STDIO taşıması üzerinden uçtan uca bir tur ekler (el sıkışma → `tools/list` → `tools/call`).
- **CI:** [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) Ruff, bir `py_compile` kontrolü ve `pytest` çalıştırır. **Yalnızca manuel** tetiklenir — Actions sekmesi → CI → Run workflow.

Sunucuyu elle, bir istemci üzerinden çalıştırmak için:

```bash
python3 context-shrink.py   # stdio sunucusunu başlatır; durdurmak için Ctrl-C
```

---

## 📚 Dokümantasyon

- [README.md](./README.md) — İngilizce sürüm.
- [README.tr.md](./README.tr.md) — bu dosya.
- [context-shrink.py](./context-shrink.py) — araç şemaları ve davranışın kaynağı.
- [CONTRIBUTING.md](./CONTRIBUTING.md) — geliştirme kurulumu, testler ve commit kuralları.
- [CHANGELOG.md](./CHANGELOG.md) — sürüm notları.
- [OPENAI-API-REFERENCE.md](./OPENAI-API-REFERENCE.md) — sunucunun dayandığı uç nokta, başlıklar ve hata biçimleri.
- [examples/python-client.py](./examples/python-client.py) — araçları listeleyip birini çağıran çalıştırılabilir bir MCP istemcisi.
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — bu dosyanın üzerine kurulduğu taşıma katmanı ve `MCPServer` API'si.

---

## 📝 Notlar

- Varsayılan bağlam sınırı: `32768` token — profilinize göre değiştirin.
- Kırpma politikası: önce en eski mesajlar; son `keep_last` mesaj her zaman korunur.
- Sıkıştırma politikası: baştaki `system` mesajları korunur, geri kalanların en eskileri özeti taşıyan tek bir `system` mesajıyla değiştirilir ve son `keep_last` mesaj aynen korunur.
- Araç yüzeyi sade MCP'dir; yani yalnızca OpenCode değil, herhangi bir MCP istemcisi sunucuyu kullanabilir.

---

## 🔁 oMLX Prompt Shrink'tan geçiş

Proje, **oMLX Prompt Shrink** adından tedarikçi-tarafsız **Context Shrink** adına
taşındı. MCP araç *adları* değişmedi (`estimate_context`, `trim_context`,
`compact_context`) ve GitHub eski URL'i yönlendirir; yani yalnızca birkaç şeye
dikkat etmek yeterli:

| Ne | Eski | Yeni |
| :--- | :--- | :--- |
| Sunucu dosyası | `omlx-prompt-shrink.py` | `context-shrink.py` |
| `mcp.json` / `opencode.jsonc` komut yolu | `…/omlx-prompt-shrink.py` | `…/context-shrink.py` |
| Araç namespace'i | `tools.oMLX_Prompt_Shrink.*` | `tools.Context_Shrink.*` |
| Depo | `omlx-prompt-shrink` | `context-shrink-mcp` |
| Ortam değişkenleri | `OMLX_SHRINK_*` / `OPENAI_SHRINK_*` | `CONTEXT_SHRINK_*` (eski adlar da çalışır) |

Çektikten sonra yerel yapılandırmanızı `context-shrink.py`'ye yöneltin (ve
kopyaladığınız bir sürüm varsa onu da güncelleyin), ardından `/reload` çalıştırın.
Mevcut `OMLX_SHRINK_*` / `OPENAI_SHRINK_*` ortam ayarları çalışmaya devam eder;
onlar için yapılandırma değişikliği zorunlu değildir.

---

## 🔗 Arka Plan

Bu sunucunun ele aldığı 32K profili ve `Prompt is too long` hatası [`mahirfatih/omlx-m1-max-benchmark`](https://github.com/mahirfatih/omlx-m1-max-benchmark) deposunda belgelenmiştir: `docs/reference/PROFILES.md` bağlam penceresinin neden 32K olduğunu açıklar, README ise bu sunucu için öneri bölümünü içerir.

---

## 🔐 İzinler ve Gizlilik

| Ayar / Anahtar | Amaç | Konum |
| :--- | :--- | :--- |
| `CONTEXT_SHRINK_BASE_URL` | OpenAI-uyumlu base URL | ortam / argüman |
| `CONTEXT_SHRINK_MODEL` | Özetleme için kullanılan model | ortam / argüman |
| `CONTEXT_SHRINK_API_KEY` | Yerel sunucu için Bearer token | ortam / argüman |
| `CONTEXT_SHRINK_TIMEOUT` | Özetleyici istek zaman aşımı (saniye) | ortam |
| `CONTEXT_SHRINK_TOKENIZER` | Token sayacı seçimi (`auto` / encoding / `heuristic`) | ortam |

> **Gizlilik:** Sunucu, yapılandırdığınız yerel OpenAI-uyumlu endpoint'e yapılan opsiyonel özetleyici çağrısı dışında **kendi başına hiçbir ağ isteği yapmaz**. Telemetri yok, analitik yok, hiçbir veri makineden çıkmaz. Tüm durum yalnızca bir araç çağrısı boyunca bellekte tutulur.

**Sürüm:** `1.0.0`

---

## 📄 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır.
