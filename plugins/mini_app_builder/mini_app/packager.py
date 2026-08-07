#!/usr/bin/env python3
"""MiniAppPackager — Package generated mini-programs into .zip archives"""

import os
import shutil
import logging

logger = logging.getLogger(__name__)


class MiniAppPackager:
    """Package mini-program output directories into downloadable .zip files.

    Usage:
        packager = MiniAppPackager(output_base='dist')
        zip_path = packager.package('douyin', 'dist/douyin/')
        # Returns: 'dist/douyin_mini_program.zip'
    """

    def __init__(self, output_base: str = 'dist'):
        self.output_base = output_base

    def package(self, platform: str, output_dir: str) -> str:
        """Package a single platform's output into a .zip file.

        Args:
            platform: Platform identifier (e.g., 'douyin', 'telegram')
            output_dir: Path to the generated files directory

        Returns:
            Absolute path to the created .zip archive

        Raises:
            FileNotFoundError: If output_dir does not exist
        """
        if not os.path.isdir(output_dir):
            raise FileNotFoundError(f'Output directory not found: {output_dir}')

        zip_name = f'{platform}_mini_program'
        zip_base = os.path.join(self.output_base, zip_name)

        # Remove existing archive if present
        if os.path.exists(zip_base + '.zip'):
            os.remove(zip_base + '.zip')

        archive_path = shutil.make_archive(zip_base, 'zip', output_dir)
        logger.info(f'[Packager] Created {archive_path}')
        return archive_path

    def package_all(self, results: dict) -> dict:
        """Package all platform results from MiniAppEngine.generate().

        Args:
            results: Output from MiniAppEngine.generate()

        Returns:
            {
                'douyin': 'dist/douyin_mini_program.zip',
                'telegram': 'dist/telegram_mini_program.zip',
                ...
            }
        """
        packages = {}
        for platform, result in results.items():
            if result.get('status') == 'completed':
                try:
                    packages[platform] = self.package(platform, result['output_dir'])
                except Exception as e:
                    logger.error(f'[Packager] Failed to package {platform}: {e}')
                    packages[platform] = None
        return packages