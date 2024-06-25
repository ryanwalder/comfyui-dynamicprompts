from __future__ import annotations

import logging
import os
from abc import ABC, abstractproperty
from collections.abc import Iterable

from dynamicprompts.sampling_context import SamplingContext
from dynamicprompts.wildcards import WildcardManager

logger = logging.getLogger(__name__)


class DPAbstractSamplerNode(ABC):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "dynamicPrompts": False}),
                "seed": ("INT", {"default": 0, "display": "number"}),
                "autorefresh": (["Yes", "No"], {"default": "No"}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, text: str, seed: int, autorefresh: str):
        # Force re-evaluation of the node
        return float("NaN")

    RETURN_TYPES = ("STRING",)
    FUNCTION = "get_prompt"
    CATEGORY = "Dynamic Prompts"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        wildcards_folder = self._find_wildcards_folder()
        self._wildcard_manager = WildcardManager(path=wildcards_folder)
        self._current_prompt = None

    def _find_wildcards_folder(self):
        """
        Find the wildcards folder.
        """
        install_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        wildcard_path = os.path.join(install_dir, "wildcards")

        if not os.path.exists(wildcard_path):
            wildcard_path = os.path.join(wildcard_path)
            os.mkdir(wildcard_path)

        return wildcard_path

    def _get_next_prompt(self, prompts: Iterable[str], current_prompt: str) -> str:
        """
        Get the next prompt from the prompts generator.
        """
        try:
            return next(prompts)
        except (StopIteration, RuntimeError):
            self._prompts = self.context.sample_prompts(current_prompt)
            try:
                return next(self._prompts)
            except StopIteration:
                logger.exception("No more prompts to generate!")
                return ""

    def has_prompt_changed(self, text: str) -> bool:
        """
        Check if the prompt has changed.
        """
        return self._current_prompt != text

    def get_prompt(self, text: str, seed: int, autorefresh: str) -> tuple[str]:
        """
        Main entrypoint for this node.
        Using the sampling context, generate a new prompt.
        """

        if seed > 0:
            self.context.rand.seed(seed)

        if text.strip() == "":
            return ("",)

        if self.has_prompt_changed(text):
            self._current_prompt = text
            self._prompts = self.context.sample_prompts(self._current_prompt)

        if self._prompts is None:
            logger.exception("Something went wrong. Prompts is None!")
            return ("",)

        if self._current_prompt is None:
            logger.exception("Something went wrong. Current prompt is None!")
            return ("",)

        new_prompt = self._get_next_prompt(self._prompts, self._current_prompt)
        print(f"New prompt: {new_prompt}")

        return (str(new_prompt),)

    @abstractproperty
    def context(self) -> SamplingContext:
        ...
