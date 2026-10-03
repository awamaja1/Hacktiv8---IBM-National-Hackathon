from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.message import Message  # <-- Wajib untuk output
import re
import json

class NaturalLanguageExtractor(Component):
    display_name = "NLP Intent Extractor"
    description = "Mengekstrak case_id, dhe_rule_version, atau JSON mentah secara instan dari bahasa natural."
    icon = "filter"
    name = "NLPIntentExtractor"

    inputs = [
        MessageTextInput(
            name="chat_input",
            display_name="Chat Input Data",
            info="Tarik kabel dari komponen [Chat Input] ke port ini.",
            value="",
        ),
    ]

    # Output diperbarui untuk memberikan sinyal bahwa tipe yang keluar adalah Message
    outputs = [
        Output(display_name="Case ID (Message)", name="out_case_id", method="extract_case_id"),
        Output(display_name="DHE Rule Version (Message)", name="out_dhe_rule", method="extract_dhe_rule"),
        Output(display_name="Document JSON (Message)", name="out_json", method="extract_json"),
    ]

    def extract_case_id(self) -> Message:
        text = self.chat_input or ""
        # Mencari pola yang diawali dengan CASE_
        match = re.search(r"(CASE_[A-Za-z0-9_]+)", text)
        result = match.group(1) if match else ""
        
        # Bungkus hasil ke dalam Message
        return Message(text=result)

    def extract_dhe_rule(self) -> Message:
        text = self.chat_input or ""
        # Mencari pola aturan BI. Jika tidak disebut, default ke PADG_16_2026
        match = re.search(r"(PADG_16_2026|PP_8_2025|BASELINE_PRE_2025)", text)
        result = match.group(1) if match else "PADG_16_2026"
        
        # Bungkus hasil ke dalam Message
        return Message(text=result)

    def extract_json(self) -> Message:
        text = self.chat_input or ""
        # Mencari blok JSON jika pengguna menempelkan payload penuh
        if "{" in text and "}" in text:
            try:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                json.loads(json_str) # Validasi sederhana
                return Message(text=json_str)
            except:
                return Message(text="")
        return Message(text="")