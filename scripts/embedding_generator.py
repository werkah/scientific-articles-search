import json
import logging
import math
import os
import zipfile
from pathlib import Path
from tqdm import tqdm
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(
        self,
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device=None,
        output_dir="data/enriched",
    ):
        import torch

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = model_name
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(
            f"Initializing SentenceTransformer model '{model_name}' on {self.device}"
        )
        self.model = SentenceTransformer(model_name, device=self.device)
        self.dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded with embedding dimension: {self.dim}")

    def _encode(self, texts, batch_size=64):
        if not texts:
            return np.array([])
        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

    def process_in_parts(self, articles, parts=5, batch_size=64, base_path=None):
        if base_path is None:
            base_path = os.path.join(self.output_dir, "enriched")
        total = len(articles)
        step = math.ceil(total / parts)
        zip_files = []
        for i in range(parts):
            start = i * step
            end = min(start + step, total)
            part_articles = articles[start:end]
            logger.info(f"Processing part {i+1}/{parts} ({start}–{end})")
            titles = [a.get("title", "") for a in part_articles]
            abstracts = [a.get("abstract", "") for a in part_articles]
            keywords = []
            for a in part_articles:
                kws = a.get("keywords", [])
                if isinstance(kws, list):
                    keywords.append(", ".join(kws))
                elif isinstance(kws, str):
                    keywords.append(kws)
                else:
                    keywords.append("")
            logger.info("Generating title embeddings...")
            title_embeddings = self._encode(titles, batch_size)
            logger.info("Generating abstract embeddings...")
            abstract_embeddings = self._encode(abstracts, batch_size)
            logger.info("Generating keyword embeddings...")
            keyword_embeddings = self._encode(keywords, batch_size)
            enriched = []
            for j, art in enumerate(tqdm(part_articles, desc="Merging embeddings")):
                enriched_article = art.copy()
                if j < len(title_embeddings):
                    enriched_article["title_embedding"] = title_embeddings[j].tolist()
                if j < len(abstract_embeddings):
                    enriched_article["abstract_embedding"] = abstract_embeddings[
                        j
                    ].tolist()
                if j < len(keyword_embeddings):
                    enriched_article["keywords_embedding"] = keyword_embeddings[
                        j
                    ].tolist()
                enriched.append(enriched_article)
            json_path = f"{base_path}_part_{i+1}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(enriched, f, ensure_ascii=False)
            zip_path = f"{base_path}_part_{i+1}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(json_path, arcname=os.path.basename(json_path))
            zip_files.append(zip_path)
            logger.info(f"Saved part {i+1} to {json_path} and compressed to {zip_path}")
            os.remove(json_path)
        return zip_files

    def generate_combined_embeddings(self, parts=5, batch_size=64):

        enriched_dir = self.output_dir
        combined_dir = os.path.join(
            os.path.dirname(enriched_dir), "combined_embeddings"
        )
        os.makedirs(combined_dir, exist_ok=True)

        existing_combined = list(Path(combined_dir).glob("combined_*.zip"))
        if existing_combined:
            logger.info(
                f"Combined embeddings already exist ({len(existing_combined)} files)"
            )
            return existing_combined

        enriched_files = sorted(Path(enriched_dir).glob("enriched_part_*.zip"))
        if not enriched_files:
            logger.error(f"No enriched files found in {enriched_dir}")
            return []

        logger.info(f"Found {len(enriched_files)} enriched files to process")
        result_files = []

        for i, zip_file in enumerate(enriched_files):
            part_num = i + 1
            logger.info(f"Processing enriched part {part_num}/{len(enriched_files)}")

            articles = []
            with zipfile.ZipFile(zip_file, "r") as zipf:
                json_files = [f for f in zipf.namelist() if f.endswith(".json")]
                if not json_files:
                    logger.warning(f"No JSON files found in {zip_file}")
                    continue

                with zipf.open(json_files[0]) as f:
                    articles = json.load(f)

            if not articles:
                logger.warning(f"No articles found in {zip_file}")
                continue

            combined_texts = []
            for article in tqdm(articles, desc="Creating combined content"):
                combined_text = self._create_combined_text(article)
                article["combined_content"] = combined_text
                combined_texts.append(combined_text)

            logger.info(
                f"Generating combined embeddings for {len(combined_texts)} articles"
            )
            combined_embeddings = self._encode(combined_texts, batch_size)

            for j, article in enumerate(articles):
                if j < len(combined_embeddings):
                    article["combined_embedding"] = combined_embeddings[j].tolist()

            output_json = os.path.join(combined_dir, f"combined_part_{part_num}.json")
            output_zip = os.path.join(combined_dir, f"combined_part_{part_num}.zip")

            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False)

            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(output_json, arcname=os.path.basename(output_json))

            os.remove(output_json)

            result_files.append(output_zip)
            logger.info(f"Saved combined embeddings to {output_zip}")

        return result_files

    def _create_combined_text(self, article):
        combined_text = ""

        if article.get("title"):
            combined_text += article["title"] + " "

        if article.get("abstract"):
            combined_text += article["abstract"] + " "

        if article.get("keywords"):
            keywords = article["keywords"]
            if isinstance(keywords, list):
                combined_text += " ".join(keywords)
            else:
                combined_text += keywords

        return combined_text.strip()
