import asyncio
import logging
import typing as t

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag

from summer_internships_scraper.models.offers import JobOffer
from summer_internships_scraper.repository.jobs import JobRepository
from summer_internships_scraper.utils import HEADERS, HOST, LOCATIONS
from summer_internships_scraper.utils.exceptions import ParsingError, ScrapingError
from summer_internships_scraper.utils.markdown_export import export_to_markdown

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Entry point for LinkedIn job offers scraper."""

    def __init__(self, host: str, logger: logging.Logger = logger) -> None:
        self.host = host
        self.logger = logger

    async def fetch_jobs(
        self,
        geo_id: str,
        keywords: str = "Summer 2025",
        session: aiohttp.ClientSession = None,
    ) -> t.Optional[t.List[JobOffer]]:
        """
        Retrieves jobs, parses them, and returns a list containing offers.

        :param geo_id: The location ID used by LinkedIn (stored internally)
        :param keywords: Keywords needed for the research
        """

        if not isinstance(geo_id, str) or not isinstance(keywords, str):
            raise TypeError("'geo_id' and 'keywords' have to be str")

        self.logger.info(
            "Fetching jobs at %s with following pattern: '%s'" % (geo_id, keywords)
        )
        keywords = self._format_keywords(keywords)
        url = f"{self.host}/?keywords={keywords}&geoId={geo_id}"

        async with session.get(
            url,
            headers=HEADERS,
            allow_redirects=True,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                raise ScrapingError(f"Error while requesting {url}")

            content = await response.text(encoding="utf-8")

            soup = BeautifulSoup(content, "html.parser")
            cards = soup.find_all("div", class_="job-search-card")

            jobs = []
            filtered_count = 0
            total_count = len(cards)

        for card in cards:
            if not self._filter_cards(card):
                filtered_count += 1
                continue

            try:
                job = self._parse_job_card(card)
                jobs.append(job)
            except Exception as e:
                raise ParsingError("Error while parsing job card") from e

        self.logger.info(
            f"Found {len(jobs)} dev jobs out of {total_count} total jobs "
            f"(filtered out {filtered_count})"
        )

        return jobs

    def _format_keywords(self, keywords: str) -> str:
        return keywords.replace(" ", "%20")

    def _parse_job_card(self, card: Tag) -> JobOffer:
        """Extracts information from a job card"""

        title = card.find("h3", class_="base-search-card__title").text.strip()
        name = card.find("h4", class_="base-search-card__subtitle").text.strip()
        location = card.find("span", class_="job-search-card__location").text.strip()
        link = card.find("a", class_="base-card__full-link")
        url = link.get("href") if link else None
        datetime_element = card.find("time")
        posted_date = datetime_element.get("datetime") if datetime_element else None

        return JobOffer(
            title=title,
            company_name=name,
            location=location,
            url=url,
            posted_date=posted_date,
            description=None,  # TODO: retrieve dev-related keywords in description
        )

    def _filter_cards(self, card: Tag) -> bool:
        """
        Filter job cards based on development-related keywords in the title.
        Must contain 'intern' and at least one tech-related keyword.
        Returns True if the card should be kept, False otherwise.
        """

        dev_keywords = {
            "software",
            "developer",
            "engineer",
            "backend",
            "frontend",
            "fullstack",
            "full-stack",
            "data",
            "engineering",
            "mobile",
            "qa",
            "security",
            "web",
            "cloud",
            "devops",
        }

        excluded_keywords = {
            "marketing",
            "sales",
            "business",
            "finance",
            "accounting",
            "hr",
            "human resources",
            "recruiter",
            "customer",
            "support",
            "service",
            "content",
            "design",
            "product manager",
            "project manager",
            "operations",
        }

        title = card.find("h3", class_="base-search-card__title")
        if not title:
            return False

        title_text = title.text.strip().lower()

        if "intern" not in title_text and "internship" not in title_text:
            return False

        if any(keyword in title_text for keyword in excluded_keywords):
            return False

        return any(keyword in title_text for keyword in dev_keywords)


async def main():
    scraper = LinkedInScraper(HOST)
    repo = JobRepository()

    async with aiohttp.ClientSession() as session:
        tasks = []
        for location, geo_id in LOCATIONS.items():
            logger.info(f"Fetching jobs for {location}")
            tasks.append(
                scraper.fetch_jobs(
                    geo_id=geo_id, keywords="Summer 2025", session=session
                )
            )

        results = await asyncio.gather(*tasks)

        total_new_jobs = 0
        for jobs in results:
            if jobs is not None:
                new_jobs, total_jobs = repo.add_jobs(jobs)
                total_new_jobs += new_jobs
                logger.info(
                    f"Added {new_jobs} new jobs. Total jobs in storage: {total_jobs}"
                )

    all_jobs = repo.get_all_jobs()
    export_to_markdown(all_jobs)
    logger.info(f"Generated markdown file with {len(all_jobs)} jobs")


if __name__ == "__main__":
    asyncio.run(main())
