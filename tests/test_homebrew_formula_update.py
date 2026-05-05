from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update-homebrew-formula.py"
SPEC = importlib.util.spec_from_file_location("update_homebrew_formula", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_canonical_resource_name() -> None:
    assert MODULE.canonical_resource_name("InquirerPy") == "inquirerpy"
    assert MODULE.canonical_resource_name("typing_extensions") == "typing-extensions"
    assert MODULE.canonical_resource_name("markdown.it_py") == "markdown-it-py"


def test_render_resource_blocks() -> None:
    rendered = MODULE.render_resource_blocks(
        [
            ("click", "https://example.com/click.tar.gz", "abc"),
            ("rich", "https://example.com/rich.tar.gz", "def"),
        ]
    )
    assert 'resource "click" do' in rendered
    assert 'url "https://example.com/click.tar.gz"' in rendered
    assert 'sha256 "def"' in rendered


def test_update_formula_text_replaces_source_and_resources() -> None:
    original = """class AgentFeed < Formula
  include Language::Python::Virtualenv

  desc "Example"
  homepage "https://example.com"
  url "https://old.example.com/agent_feed-1.0.0.tar.gz"
  sha256 "oldsha"
  license "MIT"

  depends_on "python@3.13"

  resource "old" do
    url "https://old.example.com/old.tar.gz"
    sha256 "oldresource"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "agent-feed 0.0.0", shell_output("#{bin}/agent-feed --version")
  end
end
"""
    resources = MODULE.render_resource_blocks(
        [
            ("click", "https://example.com/click.tar.gz", "abc"),
            ("rich", "https://example.com/rich.tar.gz", "def"),
        ]
    )

    updated = MODULE.update_formula_text(
        original,
        "https://new.example.com/agent_feed-1.1.0.tar.gz",
        "newsha",
        resources,
    )

    assert 'url "https://new.example.com/agent_feed-1.1.0.tar.gz"' in updated
    assert 'sha256 "newsha"' in updated
    assert 'resource "click" do' in updated
    assert 'resource "rich" do' in updated
    assert 'resource "old" do' not in updated
    assert 'assert_match "agent-feed #{version}", shell_output' in updated
