import unittest
import argparse
import sys
import os
import yaml
import base64
from unittest.mock import patch, Mock

# Add the project root to the path so we can import pygitup
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from pygitup.core.args import create_parser
from pygitup.core.config import load_config, DEFAULT_CONFIG, get_github_token, get_github_username
from pygitup.github.api import get_repo_info, create_repo, update_file
from pygitup.github.releases import generate_changelog

class TestPygitup(unittest.TestCase):
    def test_create_parser(self):
        parser = create_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_load_config_default(self):
        # Test loading default config when no file exists
        config = load_config("non_existent_file.yaml")
        self.assertEqual(config, DEFAULT_CONFIG)

    @patch('pygitup.core.config.validate_config_path', return_value=True)
    def test_load_config_custom(self, mock_validate):
        # Create a dummy config file
        custom_config_data = {
            "defaults": {
                "commit_message": "Test commit message",
                "branch": "develop"
            },
            "github": {
                "username": "testuser"
            }
        }
        # Use a path that would be valid or mock validation
        with open("test_config.yaml", "w") as f:
            yaml.dump(custom_config_data, f)

        # Test loading the custom config
        config = load_config("test_config.yaml")

        # Check that the custom values are loaded
        self.assertEqual(config["defaults"]["commit_message"], "Test commit message")
        self.assertEqual(config["defaults"]["branch"], "develop")
        self.assertEqual(config["github"]["username"], "testuser")

        # Check that the other values are the defaults
        self.assertEqual(config["batch"]["max_files"], DEFAULT_CONFIG["batch"]["max_files"])

        # Clean up the dummy config file
        os.remove("test_config.yaml")

    def test_get_github_token_from_config(self):
        config = {
            "github": {
                "token": "test_token_from_config"
            }
        }
        token = get_github_token(config)
        self.assertEqual(token, "test_token_from_config")

    def test_get_github_token_from_env(self):
        # Set an environment variable
        os.environ["GITHUB_TOKEN"] = "test_token_from_env"

        config = {
            "github": {
                "token": ""
            }
        }
        token = get_github_token(config)
        self.assertEqual(token, "test_token_from_env")

        # Unset the environment variable
        del os.environ["GITHUB_TOKEN"]

    def test_get_github_username_from_config(self):
        config = {
            "github": {
                "username": "testuser_from_config"
            }
        }
        username = get_github_username(config)
        self.assertEqual(username, "testuser_from_config")

    @patch('pygitup.github.api.requests.request')
    def test_get_repo_info(self, mock_request):
        # Set up the mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-repo", "description": "A test repo"}
        mock_request.return_value = mock_response

        # Call the function
        response = get_repo_info("testuser", "test-repo", "test_token")

        # Assert that requests.request was called correctly (with timeout=15)
        mock_request.assert_called_once_with(
            "GET",
            "https://api.github.com/repos/testuser/test-repo",
            headers={"Authorization": "token test_token", "Accept": "application/vnd.github.v3+json"},
            timeout=15
        )

        # Assert that the function returns the mock response
        self.assertEqual(response, mock_response)

    @patch('pygitup.github.api.requests.request')
    def test_create_repo(self, mock_request):
        # Set up the mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "test-repo", "html_url": "https://github.com/testuser/test-repo"}
        mock_request.return_value = mock_response

        # Call the function
        response = create_repo("testuser", "test-repo", "test_token", description="A test repo", private=True)

        # Assert that requests.request was called correctly
        mock_request.assert_called_once_with(
            "POST",
            "https://api.github.com/user/repos",
            headers={"Authorization": "token test_token", "Accept": "application/vnd.github.v3+json"},
            timeout=15,
            json={"name": "test-repo", "description": "A test repo", "private": True}
        )

        # Assert that the function returns the mock response
        self.assertEqual(response, mock_response)

    @patch('pygitup.github.api.requests.request')
    def test_update_file(self, mock_request):
        # Set up the mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"commit": {"sha": "12345"}}
        mock_request.return_value = mock_response

        # Call the function
        content = b"Hello, World!"
        response = update_file("testuser", "test-repo", "hello.txt", content, "test_token", "Update hello.txt", sha="abcde")

        # Assert that requests.request was called correctly
        encoded_content = base64.b64encode(content).decode('utf-8')
        mock_request.assert_called_once_with(
            "PUT",
            "https://api.github.com/repos/testuser/test-repo/contents/hello.txt",
            headers={"Authorization": "token test_token", "Accept": "application/vnd.github.v3+json"},
            timeout=15,
            json={"message": "Update hello.txt", "content": encoded_content, "sha": "abcde"}
        )

        # Assert that the function returns the mock response
        self.assertEqual(response, mock_response)

    @patch('pygitup.github.releases.get_commit_history')
    def test_generate_changelog(self, mock_get_commit_history):
        # Set up the mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "commit": {
                    "message": "feat: Add new feature",
                    "author": {"name": "Test User", "date": "2025-09-27T10:00:00Z"}
                }
            },
            {
                "commit": {
                    "message": "fix: Fix a bug",
                    "author": {"name": "Test User", "date": "2025-09-26T10:00:00Z"}
                }
            }
        ]
        mock_get_commit_history.return_value = mock_response

        # Call the function
        changelog = generate_changelog("testuser", "test-repo", "test_token", "v1.0.0")

        # Assert that the changelog is correct
        expected_changelog = "## Changelog for v1.0.0\n\n- feat: Add new feature (Test User on 2025-09-27)\n- fix: Fix a bug (Test User on 2025-09-26)\n"
        self.assertEqual(changelog, expected_changelog)

if __name__ == '__main__':
    unittest.main()