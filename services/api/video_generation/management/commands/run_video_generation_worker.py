import time

from django.conf import settings
from django.core.management.base import BaseCommand

from video_generation.services import (
    claim_next_video_generation_job,
    process_video_generation_job,
    recover_stale_video_generation_jobs,
)


class Command(BaseCommand):
    help = "Process durable short-video generation jobs."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one queued job, then exit.")
        parser.add_argument(
            "--poll-interval",
            type=int,
            default=settings.VIDEO_JOB_POLL_INTERVAL_SECONDS,
            help="Seconds to wait when the queue is empty.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        poll_interval = max(1, options["poll_interval"])
        self.stdout.write(self.style.SUCCESS("Video generation worker started."))

        try:
            while True:
                recovered_count = recover_stale_video_generation_jobs()
                if recovered_count:
                    self.stdout.write(f"Recovered {recovered_count} stale job(s).")

                job = claim_next_video_generation_job()
                if job is None:
                    if once:
                        return
                    time.sleep(poll_interval)
                    continue

                self.stdout.write(f"Processing video generation job #{job.id} (attempt {job.attempt_count}).")
                completed_job = process_video_generation_job(job)
                self.stdout.write(f"Job #{completed_job.id} finished with status {completed_job.status}.")
                if once:
                    return
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Video generation worker stopped."))
