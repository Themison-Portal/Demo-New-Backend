#!/usr/bin/env python3
"""
Backfill script to migrate existing chunks to 3072-dimension embeddings.

Usage:
    python scripts/backfill_embeddings.py [--batch-size 100] [--dry-run]

This script:
1. Finds all chunks without embedding_large
2. Generates 3072-dim embeddings in batches
3. Updates the database with new embeddings
4. Respects OpenAI rate limits with configurable delays

Run during low-traffic periods. The script is idempotent and can be
safely restarted if interrupted.
"""

import asyncio
import argparse
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.chunks_docling import DocumentChunkDocling
from app.core.openai import embedding_client_large

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DEFAULT_BATCH_SIZE = 100
RATE_LIMIT_DELAY = 1.0  # seconds between batches (OpenAI rate limiting)


async def count_pending_chunks(session: AsyncSession) -> int:
    """Count chunks that need embedding backfill."""
    stmt = select(DocumentChunkDocling).where(
        DocumentChunkDocling.embedding_large.is_(None)
    )
    result = await session.execute(stmt)
    return len(result.scalars().all())


async def get_pending_chunks(session: AsyncSession, batch_size: int) -> list:
    """Get a batch of chunks that need embedding backfill."""
    stmt = select(DocumentChunkDocling).where(
        DocumentChunkDocling.embedding_large.is_(None)
    ).limit(batch_size)
    result = await session.execute(stmt)
    return result.scalars().all()


async def backfill_batch(
    session: AsyncSession,
    chunks: list,
    dry_run: bool = False
) -> int:
    """
    Generate and store 3072-dim embeddings for a batch of chunks.

    Returns:
        Number of chunks updated
    """
    if not chunks:
        return 0

    # Extract text content
    texts = [chunk.content for chunk in chunks]
    chunk_ids = [chunk.id for chunk in chunks]

    logger.info(f"Generating embeddings for {len(texts)} chunks...")

    if dry_run:
        logger.info("[DRY RUN] Would generate embeddings for chunks: %s", chunk_ids[:3])
        return len(chunks)

    try:
        # Generate embeddings using the large model
        embeddings = await embedding_client_large.aembed_documents(texts)

        # Update each chunk with its new embedding
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding_large = embedding

        await session.commit()
        logger.info(f"Successfully updated {len(chunks)} chunks with 3072-dim embeddings")
        return len(chunks)

    except Exception as e:
        logger.error(f"Failed to process batch: {e}")
        await session.rollback()
        raise


async def run_backfill(batch_size: int = DEFAULT_BATCH_SIZE, dry_run: bool = False):
    """
    Main backfill loop. Processes all chunks without embedding_large.
    """
    total_processed = 0
    start_time = time.time()

    async with async_session_maker() as session:
        # Count total pending
        pending_count = await count_pending_chunks(session)
        logger.info(f"Found {pending_count} chunks pending backfill")

        if pending_count == 0:
            logger.info("No chunks need backfill. Exiting.")
            return

        batch_num = 0
        while True:
            batch_num += 1
            logger.info(f"\n--- Batch {batch_num} ---")

            # Get next batch
            chunks = await get_pending_chunks(session, batch_size)

            if not chunks:
                logger.info("No more chunks to process. Backfill complete!")
                break

            # Process batch
            processed = await backfill_batch(session, chunks, dry_run)
            total_processed += processed

            # Progress update
            elapsed = time.time() - start_time
            rate = total_processed / elapsed if elapsed > 0 else 0
            remaining = pending_count - total_processed
            eta = remaining / rate if rate > 0 else 0

            logger.info(
                f"Progress: {total_processed}/{pending_count} "
                f"({100 * total_processed / pending_count:.1f}%) | "
                f"Rate: {rate:.1f} chunks/sec | "
                f"ETA: {eta / 60:.1f} min"
            )

            # Rate limiting delay
            if not dry_run:
                logger.info(f"Waiting {RATE_LIMIT_DELAY}s for rate limiting...")
                await asyncio.sleep(RATE_LIMIT_DELAY)

    # Final summary
    elapsed = time.time() - start_time
    logger.info(f"\n{'='*50}")
    logger.info(f"Backfill complete!")
    logger.info(f"Total processed: {total_processed} chunks")
    logger.info(f"Total time: {elapsed / 60:.1f} minutes")
    logger.info(f"Average rate: {total_processed / elapsed:.1f} chunks/sec")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill 3072-dimension embeddings for existing chunks"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of chunks to process per batch (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making changes (for testing)"
    )

    args = parser.parse_args()

    logger.info("Starting embedding backfill...")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Dry run: {args.dry_run}")

    asyncio.run(run_backfill(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
