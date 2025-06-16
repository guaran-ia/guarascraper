# Guarascrapper

Web scrapper application for online Guarani text developed under the initiative UCA Autumn of Code 2025.


# Web Sources
- [Secretaría Nacional de Cultura Paraguay](https://cultura.gov.py/): part of paraguayan goverment sites
- [Secreataria de Politica Linguistica](https://spl.gov.py/gn/): part of paraguayan goverment sites
- [ABC Color](https://www.abc.com.py/): paraguayan newspaper
- [Facultad de humanidades, ciencias sociales y cultura guaraní](https://humanidades.uni.edu.py/nane-nee-guarani-ara/): paraguayan university
- [Yvy Marãe'ỹ](https://yvymaraey.edu.py/): institute for culturarl studies
- [Misa Guarani](https://misaguarani.com/): church readings
- [Portal Guarani](https://www.portalguarani.com/): history and culture of paraguay
- [Guarani Raity](https://www.guarani-raity.com.py/index.html): some sort of guarani library
- [Vikipetã](https://gn.wikipedia.org/wiki/Kuatia_%C3%91epyr%C5%A9ha): wikipedia in guarani
- [jw.org](https://www.jw.org/gug/): jehovah witnesses site
- [Ultima hora](https://www.ultimahora.com/): paraguayan newspaper 
- [Ñane Ñe'ẽ Guarani](https://guaraniete.blogspot.com/): blog about guarani
- [GuaraniMeme](https://guaranimeme.blogspot.com/): blog about guarani
- [lenguagurani](https://lenguaguarani.blogspot.com/): blog about guarani
- [Constitución](https://guaraniayvu.org/Constitution): paraguayan constitution in guarani
- [Guarani Renda](https://guaranirenda.tripod.com/index_ovetanda.htm): bilingual site
- [Sociedad Biblica Paraguay](https://guarani.global.bible/bible/c6d3311681a81388-01/MAT.1): biblical passages
- [Ministerio de Economia y Finanzas Paraguay](https://www.stp.gov.py/v1/?s=%C3%91e%C2%B4%C3%AA+): articles in guarani from a part of paraguayan goverment site


# Installation

## Prerequisites
- Python 3.12+
- pip (Python package manager)

## Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/guaran-ia/guarascrapper
   cd guarascrapper
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

   3. **Install dependencies**:
   ```bash
    pip3 install -r requirements.txt
   ```

   4. **Download the FastText language identification model**:

   ```bash
   mkdir -p src/guarani_scraper/utils/lang_model

   curl https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -o src/guarani_scraper/utils/lang_model/lid.176.bin
   ```

## Usage

### Basic Usage
To run the scraper using the included list of Guarani websites:

```bash
cd src

python3 ../cli.py --csv ../data/web_sources.csv
```
The scraped Guarani words will be saved in the `corpus` directory, with each file named after the domain from which the words were scraped.

## Configuration

You can modify the following files to adjust the scraper's behavior:

- **`src/guarani_scraper/settings.py`**: Adjust crawling settings like delay, throttling, and user agent
- **`src/guarani_scraper/guarani_scraper/utils/lang_detector.py`**: Fine-tune the language detection logic
- **`data/web_sources.csv`**: Add or remove websites to be scraped