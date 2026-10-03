import json
from langflow.custom import Component
from langflow.inputs import StrInput
from langflow.template import Output
from langflow.schema import Data

class CleanPayloadBuilderComponent(Component):
    display_name = "API Message Payload Builder"
    description = "Mengekstrak teks murni dari objek Message dan membangun payload API yang bersih."
    icon = "braces"

    inputs = [
        StrInput(
            name="case_id_message",
            display_name="Case ID (Message)",
            info="Hubungkan objek Message berisi Case ID.",
            input_types=["Message", "Text"],
            value=""
        ),
        StrInput(
            name="dhe_version_message",
            display_name="DHE Rule Version (Message)",
            info="Hubungkan objek Message berisi DHE Rule Version.",
            input_types=["Message", "Text"],
            value="PADG_16_2026"
        ),
        StrInput(
            name="document_message",
            display_name="Document Data (Message)",
            info="Hubungkan objek Message berisi JSON string teks dokumen.",
            input_types=["Message", "Text"],
            value=""
        ),
    ]

    outputs = [
        Output(display_name="Payload Data", name="payload_data", method="build_payload"),
    ]

    def _extract_pure_text(self, input_data) -> str:
        """Fungsi pembantu untuk mengekstrak teks murni dari berbagai bentuk tipe data Langflow."""
        if not input_data:
            return ""
            
        # Jika berupa string biasa
        if isinstance(input_data, str):
            return input_data
            
        # Jika berupa dictionary atau objek tiruan dict dari Message
        if isinstance(input_data, dict) or hasattr(input_data, "get"):
            if hasattr(input_data, "get"):
                text_val = input_data.get("text")
                if not text_val and input_data.get("data"):
                    text_val = input_data.get("data", {}).get("text")
                if text_val:
                    return str(text_val)
                    
        # Jika berupa objek kelas Message murni Langflow yang memiliki atribut .text
        if hasattr(input_data, "text"):
            return str(input_data.text)
            
        return str(input_data)

    def build_payload(self) -> Data:
        # Ekstrak string bersih dari masing-masing input objek Message
        case_id = self._extract_pure_text(self.case_id_message)
        dhe_rule_version = self._extract_pure_text(self.dhe_version_message)
        document_text = self._extract_pure_text(self.document_message)
        
        # Bersihkan string dokumen dari pembungkus markdown block ```json jika dihasilkan oleh LLM
        if "```" in document_text:
            document_text = document_text.replace("```json", "").replace("```", "").strip()

        # --- PERBAIKAN KRUSIAL ---
        # Ubah string JSON kembali menjadi dictionary Python agar dikirim sebagai Nested JSON Object
        parsed_document_data = ""
        if document_text.startswith("{"):
            try:
                parsed_document_data = json.loads(document_text)
            except json.JSONDecodeError:
                parsed_document_data = document_text  # Fallback jika ternyata string rusak

        # Menyusun struktur payload final yang bersih dari metadata
        payload = {
            "case_id": case_id,
            "dhe_rule_version": dhe_rule_version,
            # Jika parsed_document_data valid, gunakan itu (dict). Jika kosong, biarkan string kosong.
            "document_data": parsed_document_data if parsed_document_data else document_text
        }
        
        # Kembalikan sebagai Data Object Langflow agar terbaca oleh API Request
        return Data(data=payload)