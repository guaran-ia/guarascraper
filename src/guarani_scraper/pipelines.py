# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
from itemadapter import ItemAdapter


class GuaraniScraperPipeline:
    """
    Pipeline for processing and storing scraped Guarani words.

    Words are saved to text files in the 'corpus' directory,
    with each file named after the domain from which the words were scraped.
    """

    def __init__(self):
        """
        Initialize the pipeline by creating the corpus directory
        and preparing the file handles dictionary.
        """
        self.files = {}

        # Use absolute path to ensure consistency
        self.corpus_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "corpus")
        os.makedirs(self.corpus_dir, exist_ok=True)

    def process_item(self, item, spider):
        """
        Process a GuaraniWord item by writing it to the appropriate file.

        Words from the same domain are written to the same file.

        Args:
            item (GuaraniWord): The item containing a scraped Guarani word
            spider (Spider): The spider that scraped this item

        Returns:
            GuaraniWord: The processed item
        """
        adapter = ItemAdapter(item)
        domain = adapter["domain"]

        if domain not in self.files:
            filepath = os.path.join(self.corpus_dir, f"{domain}.txt")
            self.files[domain] = open(filepath, "w", encoding="utf-8")

        self.files[domain].write(f"{adapter['word']}\n")
        return item

    def close_spider(self, spider):
        """
        Clean up when the spider finishes by closing all open files.

        Args:
            spider (Spider): The spider that has finished running
        """
        for file in self.files.values():
            file.close()
