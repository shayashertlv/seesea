import os
import unittest
from dotenv import load_dotenv

# Ensure .env is loaded for Config import
load_dotenv()

class TestProjectConfig(unittest.TestCase):
    def test_env_config_is_loaded(self):
        # Import here to ensure .env is loaded first
        from app.config import Config
        # DATABASE_URL should come from .env in this repo
        self.assertTrue(
            Config.SQLALCHEMY_DATABASE_URI.startswith("postgresql://"),
            msg=f"Expected PostgreSQL URL from .env, got: {Config.SQLALCHEMY_DATABASE_URI}"
        )
        # Secret key should match .env value
        self.assertEqual(
            Config.SECRET_KEY,
            os.environ.get("FLASK_SECRET_KEY"),
            "FLASK_SECRET_KEY from .env should be reflected in Config"
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
