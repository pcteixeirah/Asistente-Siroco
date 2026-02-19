# Análisis: Estrategias de Rotación de Proxies para SIROCO

## Contexto del Problema

YouTube emplea un sistema multicapa de defensa anti-bot:

```mermaid
graph TD
    A["Request from yt-dlp"] --> B{"Layer 1: IP Reputation"}
    B -->|Clean IP| C{"Layer 2: Behavioral Analysis"}
    B -->|Flagged IP| D["HTTP 403 Forbidden"]
    C -->|Human-like| E{"Layer 3: Token Validation"}
    C -->|Bot-like| D
    E -->|Valid PO Token| F["200 OK — Audio Stream"]
    E -->|Missing/Invalid| G["Sign in to confirm"]
```

Nuestro sistema fue baneado en **Layer 1** (IP Reputation) tras ~1,500 requests consecutivos desde la misma IP.

---

## Estrategia A: Servicio de Proxy Rotativo Gestionado (Recomendada)

**Concepto**: Contratar un servicio (BrightData, Smartproxy, Oxylabs) que expone un único endpoint gateway. Cada request sale por una IP residencial diferente automáticamente.

**Proveedores Seleccionados para SIROCO**:

1. **BrightData** (Testing): Para validación inmediata.
2. **DataImpulse** (Producción): Para despliegue a escala (costo eficiente ~$1/GB).

### Implementación

```
config.yaml:
  proxy_rotation:
    mode: "gateway"
    gateway_url: "http://user:pass@gw.dataimpulse.com:823"
```

### Pros

| Ventaja | Detalle |
|:--|:--|
| **Simplicidad** | Una sola URL. Sin gestión de pool |
| **IPs Residenciales** | Pasan como tráfico doméstico real |
| **Rotación Automática** | El servicio maneja la rotación |
| **Escalabilidad** | Soporta miles de requests/hora |
| **Uptime Garantizado** | SLA comercial (99.9%+) |

### Contras

| Vulnerabilidad | Impacto | Mitigación |
|:--|:--|:--|
| **Costo** | $10-75/GB (residencial) | Low-fi audio = ~0.5MB/track. 1,000 tracks ≈ 500MB ≈ $5-37 |
| **Dependencia Externa** | Si el servicio cae, SIROCO se detiene | Fallback a modo `none` |
| **Latencia** | +200-500ms por request | Insignificante vs. tiempo de descarga |
| **TOS de YouTube** | Sigue siendo scraping; riesgo legal teórico | Uso personal/académico |
| **Credenciales en config** | `user:pass` en texto plano | Usar variables de entorno |

> [!TIP]
> **Costo estimado para SIROCO**: Con audio low-fi (~0.5MB/track), procesar 1,000 tracks con DataImpulse costará **menos de $1**.

---

## Estrategia B: Pool Propio de Proxies (Lista Local)

**Concepto**: Mantener un archivo `proxies.txt` con una lista de proxies HTTP/SOCKS5 (gratuitos o comprados en bulk). SIROCO los rota internamente.

### Pros

| Ventaja | Detalle |
|:--|:--|
| **Control Total** | Tú decides qué IPs usar y cuándo rotar |
| **Sin Dependencia** | No depende de un servicio externo |
| **Costo Variable** | Desde $0 (Tor) hasta ~$2/proxy/mes |

### Contras

| Vulnerabilidad | Impacto | Mitigación |
|:--|:--|:--|
| **Mantenimiento** | Proxies mueren. Debes verificar y reemplazar | Health check automático |
| **Calidad Inconsistente** | Proxies gratuitos = lentos, inestables | Usar solo pagados |
| **IPs Datacenter** | YouTube detecta IPs de datacenter fácilmente | Comprar residenciales |

> [!WARNING]
> **Proxies gratuitos**: Extremadamente riesgosos. Son lentos, inestables, y a menudo son honeypots que interceptan tráfico. **No recomendado para producción**.

---

## Estrategia C: Autenticación con Cookies / PO Token

**Concepto**: En lugar de rotar IPs, autenticarse como un usuario legítimo de YouTube enviando cookies de sesión y un PO Token (Proof of Origin).

### Implementación

```
config.yaml:
  paths:
    cookies: "setup/cookies.txt"
```

### Pros

| Ventaja | Detalle |
|:--|:--|
| **Costo Cero** | Sin servicios externos |
| **Acceso a Contenido Restringido** | Age-gated, members-only |
| **Menor Detección** | YouTube trata requests autenticados con más tolerancia |

### Contras

| Vulnerabilidad | Impacto | Mitigación |
|:--|:--|:--|
| **Cookies Expiran** | YouTube rota cookies cada ~24h | Re-exportar periódicamente |
| **Riesgo de Cuenta** | YouTube puede banear la cuenta | Usar cuenta throwaway |
| **No Escala** | Una cuenta = un "usuario". Límites siguen siendo bajos (~200-500/día) | Combinar con proxy |

> [!CAUTION]
> **No es suficiente por sí sola** para 1,000+ tracks. YouTube limita incluso usuarios autenticados a ~200-500 downloads/día. Debe combinarse con Estrategia A o B.

---

## Recomendación Arquitectónica

### Estrategia Óptima: **A + C Combinadas**

```mermaid
graph LR
    A["main_proxy.py"] --> B["LowFiDownloader"]
    B --> C{"ProxyPool\n(Gateway Mode)"}
    C --> D["Smartproxy/DataImpulse Gateway\n+ cookies.txt"]
    D --> E["YouTube CDN"]
    E -->|200 OK| F["AudioAnalyzer"]
    E -->|403| G["Rotate + Retry"]
    G --> C
```

1. **Base**: Servicio de proxy rotativo gestionado (Gateway) para IPs residenciales limpias.
2. **Complemento**: Cookies exportadas para reducir la tasa de desafíos.
3. **Fallback**: Si el gateway falla, el sistema opera sin proxy (modo `none`) pero con delays agresivos.

**Costo estimado**: ~$6-8 por ejecución de 1,000 tracks (Smartproxy) o <$1 (DataImpulse). Reusable mensualmente.
