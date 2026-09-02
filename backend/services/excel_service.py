import os
import re
from typing import List, Dict, Tuple, Optional

import pandas as pd
import phonenumbers


class ExcelService:
    """Parse and validate Excel contact files."""

    def parse_excel(self, file_path: str) -> Tuple[List[Dict], List[str]]:
        """
        Parse Excel file expecting:
          Column A – Person Name
          Column B – Phone Number

        Returns (contacts, errors).
        """
        errors: List[str] = []
        contacts: List[Dict] = []

        try:
            df = pd.read_excel(file_path, header=None, dtype=str)
        except Exception as exc:
            raise ValueError(f"Cannot read Excel file: {exc}") from exc

        if df.empty:
            raise ValueError("The Excel file is empty.")

        if df.shape[1] < 2:
            raise ValueError(
                "The Excel file must have at least 2 columns: "
                "Column A = Name, Column B = Phone."
            )

        # Auto-detect header row
        first_val = str(df.iloc[0, 0]).strip().lower()
        header_keywords = {"name", "שם", "שם פרטי", "שם מלא", "person", "contact", "full name"}
        start_row = 1 if first_val in header_keywords else 0

        seen_phones: set = set()

        for idx in range(start_row, len(df)):
            row = df.iloc[idx]
            name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            phone_raw = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

            # Skip fully empty rows
            if (not name or name == "nan") and (not phone_raw or phone_raw == "nan"):
                continue

            display_row = idx + 1

            # Validate name
            if not name or name == "nan":
                errors.append(f"Row {display_row}: Missing name.")
                continue
            if len(name) < 2:
                errors.append(f"Row {display_row}: Name '{name}' is too short.")
                continue

            # Validate phone
            if not phone_raw or phone_raw == "nan":
                errors.append(f"Row {display_row}: Missing phone number for '{name}'.")
                continue

            normalized, phone_err = self._normalize_phone(phone_raw, display_row)
            if phone_err:
                errors.append(phone_err)
                continue

            # Duplicates
            if normalized in seen_phones:
                errors.append(
                    f"Row {display_row}: Duplicate phone number {normalized} for '{name}'."
                )
                continue

            seen_phones.add(normalized)
            contacts.append(
                {"name": name, "phone": normalized, "original_phone": phone_raw}
            )

        return contacts, errors

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _normalize_phone(
        self, phone: str, row_num: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Clean and validate a phone number string."""
        # Strip Excel float artefact (052000000 → 052000000.0 → 052000000)
        cleaned = re.sub(r"\.0+$", "", phone.strip())
        # Remove formatting characters
        digits = re.sub(r"[\s\-\(\)\+\.]", "", cleaned)

        # Local → international. DEFAULT_COUNTRY_CODE makes this portable to
        # any country (972 = Israel, 44 = UK, 1 = US/CA, …).
        cc = os.getenv("DEFAULT_COUNTRY_CODE", "972").lstrip("+")
        if re.match(r"^0[0-9]{9}$", digits):
            # National format with trunk 0:  0XX-XXXXXXX → <cc>XXXXXXXXX
            digits = cc + digits[1:]
        elif re.match(r"^[1-9][0-9]{8}$", digits):
            # Bare 9-digit subscriber number, no trunk 0 and no country code
            digits = cc + digits
        elif digits.startswith(cc):
            pass  # already international
        elif phone.strip().startswith("+"):
            digits = re.sub(r"[^\d]", "", phone)

        # Validate with the phonenumbers library
        try:
            num_str = digits if digits.startswith("+") else "+" + digits
            parsed = phonenumbers.parse(num_str, None)
            if phonenumbers.is_valid_number(parsed):
                return (
                    str(parsed.country_code) + str(parsed.national_number),
                    None,
                )
        except phonenumbers.NumberParseException:
            pass

        # phonenumbers rejected the number — don't silently accept it.
        # A full international number is at least 10 digits; anything shorter
        # cannot be valid regardless of country.
        if len(digits) < 10:
            return None, f"Row {row_num}: Phone number '{phone}' is too short to be valid (got {len(digits)} digits, need at least 10)."

        # Loose fallback for international numbers phonenumbers doesn't know.
        # It must still LOOK like an international number, or malformed input
        # sails through unnormalized and fails later at send time instead of here:
        #   - digits only (a stray letter must not survive)
        #   - no leading 0 (that means normalization above did not match, e.g. an
        #     11-digit "0XX-XXXXXXXX" with one digit too many)
        if 10 <= len(digits) <= 15 and digits.isdigit() and not digits.startswith("0"):
            return digits, None

        return None, f"Row {row_num}: Invalid phone number '{phone}'."
