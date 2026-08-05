from pathlib import Path


class KnowledgeRetriever:
    """
    Retrieves species-specific care guidance from the local knowledge base.
    Falls back to general veterinary guidance when no matching species exists.
    """

    def __init__(self, knowledge_folder="knowledge"):
        self.knowledge_folder = Path(knowledge_folder)

    def _read_file(self, filename):
        filepath = self.knowledge_folder / filename
        if not filepath.exists():
            return ""
        with open(filepath, "r", encoding="utf-8") as file:
            return file.read()
        
    def retrieve(self, species: str):
        """
        Returns:
            {
                "species": "...",
                "content": "...",
                "confidence": "...",
                "fallback": bool
            }
        """
        if species is None:
            species = "other"
        species = species.lower().strip()
        mapping = {
            "dog": "dog_care.md",
            "cat": "cat_care.md",
            "fish": "fish_care.md",
        }
        if species in mapping:
            filename = mapping[species]
            return {
                "species": species,
                "content": self._read_file(filename),
                "confidence": "High",
                "fallback": False,
            }
        return {
            "species": species,
            "content": self._read_file("veterinary_guidelines.md"),
            "confidence": "Medium",
            "fallback": True,
        }