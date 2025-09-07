import json
import os
import re
import requests
import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

try:
    from langdetect import detect, DetectorFactory
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 0
    HAS_LANGDETECT = True
except ImportError:
    HAS_LANGDETECT = False


class DataProcessor:

    def find_unique_entries(self, smaller_file, larger_file, output_file=None):
        with open(smaller_file, "r", encoding="utf-8") as f1, open(
            larger_file, "r", encoding="utf-8"
        ) as f2:
            data1, data2 = json.load(f1), json.load(f2)
        ids1 = {str(item["id"]) for item in data1}
        ids2 = {str(item["id"]) for item in data2}
        unique_entries = [item for item in data1 if str(item["id"]) in ids1 - ids2]
        if output_file:
            with open(output_file, "w", encoding="utf-8") as output:
                json.dump(unique_entries, output, ensure_ascii=False, indent=4)
            print(f"Number of unique entries: {len(unique_entries)}")
            print(f"Unique entries saved to: {output_file}")
        return unique_entries

    def compare_json_files(self, file1, file2, output_prefix=None):
        with open(file1, "r", encoding="utf-8") as f1, open(
            file2, "r", encoding="utf-8"
        ) as f2:
            data1, data2 = json.load(f1), json.load(f2)
        dict1 = {item["id"]: item for item in data1}
        dict2 = {item["id"]: item for item in data2}
        common_ids = set(dict1.keys()).intersection(dict2.keys())
        common_entries = [dict1[id] for id in common_ids]
        unique_to_file1 = [dict1[id] for id in set(dict1.keys()) - set(dict2.keys())]
        unique_to_file2 = [dict2[id] for id in set(dict2.keys()) - set(dict1.keys())]
        if output_prefix:
            for suffix, data in [
                ("common", common_entries),
                ("unique_to_file1", unique_to_file1),
                ("unique_to_file2", unique_to_file2),
            ]:
                out_file = f"{output_prefix}_{suffix}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                print(
                    f"{suffix.replace('_', ' ').title()} entries: {len(data)} saved to '{out_file}'"
                )
        return common_entries, unique_to_file1, unique_to_file2

    def merge_json_files(self, input_files, output_file=None):
        merged_data = []
        seen_ids = set()
        duplicate_entries = []
        for file in input_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    for entry in json.load(f):
                        if entry.get("id") in seen_ids:
                            duplicate_entries.append(entry)
                        else:
                            seen_ids.add(entry["id"])
                            merged_data.append(entry)
            except Exception as e:
                print(f"Error processing file {file}: {e}")
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
            print(
                f"Merged data from {len(input_files)} files. Result saved to {output_file}"
            )
            print(
                f"Detected {len(duplicate_entries)} duplicates. Unique IDs: {len(seen_ids)}"
            )
            if duplicate_entries:
                dup_file = f"{output_file.split('.')[0]}_duplicates.json"
                with open(dup_file, "w", encoding="utf-8") as f:
                    json.dump(duplicate_entries, f, ensure_ascii=False, indent=4)
                print(f"Duplicates saved to file: {dup_file}")
        return merged_data, duplicate_entries, len(seen_ids)

    def find_missing_ids(self, file_path, output_file=None):
        with open(file_path, "r", encoding="utf-8") as f:
            ids = [int(item["id"]) for item in json.load(f) if "id" in item]
        missing_ids = sorted(set(range(1, max(ids) + 1)) - set(ids))
        print(f"Highest ID: {max(ids)}. Number of missing IDs: {len(missing_ids)}")
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(missing_ids, f, ensure_ascii=False, indent=4)
            print(f"Missing IDs saved to: {output_file}")
        return missing_ids

    def generate_missing_urls(
        self,
        existing_file,
        max_id,
        base_url="https://badap.agh.edu.pl",
        output_file=None,
    ):
        try:
            with open(existing_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_ids = {int(item["id"]) for item in existing_data if "id" in item}
            missing_ids = sorted(set(range(1, max_id + 1)) - existing_ids)
            missing_urls = [
                {"id": str(id_num), "url": f"{base_url}/publikacja/{id_num}"}
                for id_num in missing_ids
            ]
            print(f"Existing IDs: {len(existing_ids)}")
            print(f"Missing IDs below {max_id}: {len(missing_ids)}")
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(missing_urls, f, ensure_ascii=False, indent=4)
                print(f"Missing URLs saved to: {output_file}")
            return missing_urls
        except Exception as e:
            print(f"Error generating missing URLs: {e}")
            return []

    def count_articles(self, input_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
            article_count = len(articles)
            print(f"Number of articles in '{input_file}': {article_count}")
            return article_count
        except Exception as e:
            print(f"Error: {e}")
            return 0

    def find_titles_by_ids(self, id_file, articles_file, output_file):
        try:
            with open(id_file, "r", encoding="utf-8") as f:
                ids_data = json.load(f)
            with open(articles_file, "r", encoding="utf-8") as f:
                articles_data = json.load(f)
            ids_to_find = {item["id"] for item in ids_data}
            matching_articles = [
                {"id": article["id"], "title": article.get("title", "No title")}
                for article in articles_data
                if article["id"] in ids_to_find
            ]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(matching_articles, f, ensure_ascii=False, indent=4)
            print(f"Matching titles saved to: {output_file}")
        except Exception as e:
            print(f"Error: {e}")

    def detect_language(self, text):
        if not HAS_LANGDETECT:
            return "unknown"
        try:
            if text and text.strip():
                return detect(text)
            return "unknown"
        except LangDetectException:
            return "unknown"

    def analyze_languages(self, data, target_language="pl", field="keywords"):
        if not HAS_LANGDETECT:
            print("langdetect unavailable")
            return []
        target_articles = []
        for article in data:
            content = article.get(field, [])
            if not content:
                continue
            content_str = (
                ", ".join(content)
                if field == "keywords" and isinstance(content, list)
                else content
            )
            detected_lang = self.detect_language(content_str)
            if detected_lang == target_language:
                target_articles.append(
                    {
                        "id": article["id"],
                        f"{field}_lang": detected_lang,
                        field: content,
                    }
                )
        return target_articles

    def fetch_titles(self, article_url):
        try:
            response = requests.get(article_url)
            if response.status_code != 200:
                return {"title": "No title", "title2": "No title"}
            soup = BeautifulSoup(response.text, "lxml")
            title = "No title"
            title2 = "No title"
            bibliographic_section = soup.find(
                "h2", string=re.compile("Opis bibliograficzny", re.IGNORECASE)
            )
            if bibliographic_section:
                parent_div = bibliographic_section.find_next("div")
                if parent_div:
                    main_title_span = parent_div.find("span", {"title": "tytuł"})
                    if main_title_span:
                        title = main_title_span.get_text(strip=True)
                    parallel_title_span = parent_div.find(
                        "span", {"title": "tytuł równoległy"}
                    )
                    if parallel_title_span:
                        title2 = parallel_title_span.get_text(strip=True)
            return {"title": title, "title2": title2}
        except Exception as e:
            return {"title": "No title", "title2": "No title"}

    def update_titles(self, input_file, output_file, temp_file="temp.json"):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            updated_count = 0
            for index, entry in enumerate(data):
                if (
                    "title" not in entry
                    or "title2" not in entry
                    or entry.get("title") == "No title"
                    or entry.get("title2") == "No title"
                ):
                    titles = self.fetch_titles(entry["url"])
                    entry["title"] = titles["title"]
                    entry["title2"] = titles["title2"]
                    updated_count += 1
                if (index + 1) % 10 == 0:
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Updated {updated_count} titles. Result saved to: {output_file}")
        except Exception as e:
            print(f"Error: {e}")

    def clean_titles(self, input_file, output_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for article in data:
                if "title" in article:
                    original_title = article["title"]
                    cleaned_title = re.sub(r"^\[|\]$", "", original_title.strip())
                    article["title"] = cleaned_title
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"Titles cleaned. Result saved to: {output_file}")
        except Exception as e:
            print(f"Error: {e}")

    def segregate_articles(self, input_file, filtered_file, specific_words_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                articles = json.load(f)
            polish_chars = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")
            keywords = re.compile(
                r"\b(of|the|and|for|in|with|using|while|what|is|from|or|not|how|at|about|between|after|an|as|it|its|that|this|these|those|into|onto|through|under|above|over|before|during|since|among|against|without|who|whom|which|why|where|when|has|have|had|be|been|am|are|was|were|does|did|can|could|shall|should|may|might|will|would|must|nor|neither|some|any|each|every|all|both|many|few|several|none|via|towards|thus|therefore|hence|such|based)\b",
                re.IGNORECASE,
            )
            specific_words = re.compile(r"\b(a|to|by|on|no)\b", re.IGNORECASE)
            articles_to_filter = []
            articles_to_keep = []
            articles_with_specific_words = []
            for article in articles:
                title = article.get("title", "")
                has_polish_chars = bool(polish_chars.search(title))
                has_keywords = bool(keywords.search(title))
                has_specific_words = bool(specific_words.search(title))
                if has_specific_words:
                    articles_with_specific_words.append(article)
                elif (not has_polish_chars and not has_keywords) or (
                    has_polish_chars and not has_keywords
                ):
                    articles_to_filter.append(article)
                else:
                    articles_to_keep.append(article)
            with open(filtered_file, "w", encoding="utf-8") as f:
                json.dump(articles_to_filter, f, ensure_ascii=False, indent=4)
            with open(specific_words_file, "w", encoding="utf-8") as f:
                json.dump(articles_with_specific_words, f, ensure_ascii=False, indent=4)
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(articles_to_keep, f, ensure_ascii=False, indent=4)
            print(f"Moved {len(articles_to_filter)} articles to: {filtered_file}")
            print(f"Articles with specific words saved to: {specific_words_file}")
            print(f"Original file updated: {input_file}")
        except Exception as e:
            print(f"Error: {e}")

    def filter_articles_with_authors(self, input_file, output_file, skipped_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            original_count = len(data)
            filtered_data = [article for article in data if article.get("authors")]
            skipped_data = [article for article in data if not article.get("authors")]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=4)
            with open(skipped_file, "w", encoding="utf-8") as f:
                json.dump(skipped_data, f, ensure_ascii=False, indent=4)
            print(
                f"Original article count: {original_count}, with authors: {len(filtered_data)}, without authors: {len(skipped_data)}"
            )
        except Exception as e:
            print(f"Error: {e}")

    def filter_articles_with_titles(self, input_file, output_file, skipped_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            original_count = len(data)
            filtered_data = [
                article
                for article in data
                if article.get("title") not in ["No title", "Brak tytułu"]
            ]
            skipped_data = [
                article
                for article in data
                if article.get("title") in ["No title", "Brak tytułu"]
            ]
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=4)
            with open(skipped_file, "w", encoding="utf-8") as f:
                json.dump(skipped_data, f, ensure_ascii=False, indent=4)
            print(
                f"Original count: {original_count}, after filtering: {len(filtered_data)}, skipped: {len(skipped_data)}"
            )
        except Exception as e:
            print(f"Error: {e}")


