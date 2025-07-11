from datetime import date
from models import Vaccine, Immunization
from typing import List

# ⏳ Изчисляване на възраст в месеци
def calculate_age_in_months(birth_date: date) -> int:
    today = date.today()
    return (today.year - birth_date.year) * 12 + (today.month - birth_date.month)

# 🧠 Връща препоръчителните задължителни ваксини за тази възраст
def required_mandatory_vaccines(age_months: int, all_vaccines: List[Vaccine]) -> List[Vaccine]:
    required = []
    for vaccine in all_vaccines:
        if vaccine.is_mandatory:
            # Специален случай: 18–24м само ако има минала 1г от предишната задължителна
            if 18 <= age_months <= 24:
                required.append(vaccine) if vaccine.recommended_month == 18 else None
            elif age_months >= vaccine.recommended_month:
                required.append(vaccine)
    return required
