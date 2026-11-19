---
source_hash: e2c7112db6c41d20df8b36d2d29c2ab43a5ecb4a
---

# Kurulum { #install }

## İndirme { #download }

Sisteminize uygun dosyayı
[Releases sayfasından](https://github.com/mezinster/optar/releases/latest)
indirin. Aşağıdaki `<tag>` sürümü gösterir, örneğin `v0.5.0`.

| Sistem | Masaüstü uygulaması | Komut satırı |
|---|---|---|
| Linux | `optar-gui-<tag>-linux-x86_64` | `optar-<tag>-linux-x86_64` |
| macOS (Apple silicon) | `optar-gui-<tag>-macos-arm64.zip` | `optar-<tag>-macos-arm64` |
| Windows | `optar-gui-<tag>-windows-x86_64.exe` | `optar-<tag>-windows-x86_64.exe` |

Her biri tek bir dosyadır ve başka hiçbir şeyin kurulmasını gerektirmez.

- **Linux:** önce dosya üzerinde `chmod +x` komutunu çalıştırın.
- **macOS:** komut satırı dosyası üzerinde `chmod +x` komutunu çalıştırın.
  Uygulamayı zip arşivinden çıkarın ve açmayı deneyin. Programlar imzasız
  olduğu için macOS açmayı reddedebilir: Sistem Ayarları'nı, ardından
  Gizlilik ve Güvenlik'i açın ve “Yine de Aç” seçeneğini seçin (eski macOS
  sürümlerinde uygulamaya sağ tıklayın ve Aç'ı seçin).
- **Windows:** programlar imzasız olduğu için Windows ilk çalıştırmada uyarı
  verebilir.

## Kaynak koddan { #from-source }

Python 3.12 ya da daha yeni bir sürüm ve deponun bir kopyası gerekir.

Komut satırı programı (numpy ve Pillow'u da kurar):

    pip install .

Masaüstü uygulamasını da kurmak için:

    pip install '.[gui]'
    optar-gui

## Çalıştığını kontrol etme { #check-that-it-works }

`optar --version` ve `optar-gui --version` sürüm numarasını gösterir.

`optar-gui --self-test` uygulamayı ekran olmadan başlatır ve sayfaları
kodlayıp okuyabildiğini kontrol eder.
