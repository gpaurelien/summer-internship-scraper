import hashlib
import typing as t
from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobOffer:
    title: str
    company_name: str
    location: str
    posted_date: datetime
    description: t.Optional[str]
    url: str

    def to(self):
        return {k: v for k, v in self.__dict__.items()}

    def get_hash(self) -> str:
        """
        Compute a unique hash for the job offer based on
        company name, position title, and location.
        """
        content = f"{self.company_name}{self.title}{self.location}".encode("utf-8")
        return hashlib.md5(content).hexdigest()
