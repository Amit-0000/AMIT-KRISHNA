from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover — type-checking only, never imported at runtime.
    from api.inference.confidence import ConfidenceResult
    from api.inference.explainability import ExplanationResult
    from api.inference.feature_extraction import ExtractedFeature
    from api.inference.inference import InferenceResult


@dataclass(frozen=True)
class AdapterMetadata:
    """Everything about a detector architecture that used to live as
    hardcoded constants scattered across api.inference — now declared once,
    per architecture, on the adapter that owns it. api.inference.model_registry
    reads this at registration time to populate the corresponding
    ModelVersion row, so the *database* (not this class) remains the runtime
    source of truth every pipeline run actually reads from — this exists so
    that row never has to be filled in by hand."""

    architecture: str
    checkpoint_filename: str
    feature_extractor_name: str
    feature_extractor_version: str
    input_shape: tuple[int, ...]
    preprocessing_version: str
    supports_explainability: bool
    # This architecture's native label vocabulary -> VoiceGuard's canonical
    # ('bonafide' | 'spoof'), e.g. {"Genuine": "bonafide", "Deepfake": "spoof"}.
    # Applied inside convert_prediction(), never downstream — see that
    # method's docstring below.
    label_mapping: dict[str, str]
    default_threshold: float


class ModelAdapter(ABC):
    """The single seam between VoiceGuard's model-agnostic AI orchestration
    (api.inference.jobs, api.inference.confidence, api.inference.result_writer,
    the router, the frontend — none of which import this module or any
    concrete adapter) and one specific detector architecture.

    Adding a new architecture to VoiceGuard means: implement this interface,
    register it with api.inference.adapters.registry.register_adapter, add
    its checkpoint to the model_versions table. Nothing in
    api.inference.model_loader, api.inference.jobs, api.inference.confidence,
    api.inference.result_writer, the API router, or the frontend needs to
    change — see api.inference.adapters.registry for why that's true even
    for model_loader, which used to import LCNN directly."""

    @property
    @abstractmethod
    def architecture(self) -> str:
        """Must exactly match the string stored in ModelVersion.architecture
        for every model this adapter should be selected for — this is the
        adapter registry's dispatch key (see
        api.inference.adapters.registry.get_adapter)."""

    @abstractmethod
    def load_model(self, checkpoint_path: Path, device: Any) -> Any:
        """Instantiate this architecture, load `checkpoint_path`'s
        state_dict onto it, move it to `device`, set eval mode, and return
        the raw model object. File existence and checksum integrity are
        already verified by the caller (api.inference.model_loader) before
        this is ever invoked — implementations only need to handle their
        own architecture-specific instantiation and loading. Any exception
        raised here is caught by the caller and re-raised as
        ModelNotAvailableError, so implementations don't need their own
        try/except for a missing ML runtime or a corrupt checkpoint."""

    @abstractmethod
    def feature_extractor(self) -> tuple[str, str]:
        """The (name, version) key — as registered in
        api.inference.feature_extraction's extractor registry — this
        architecture's checkpoint was trained against. Read once at model
        registration time (api.inference.model_registry) and stored on the
        ModelVersion row; api.inference.jobs reads it from there at runtime,
        not from this method directly."""

    def preprocess(self, waveform: Any) -> Any:
        """Hook for architecture-specific adjustment to the waveform
        api.inference.preprocessing.run_preprocessing already produced
        (decoded, resampled to 16kHz, mono, silence-trimmed, fixed-length —
        none of which is architecture-specific: every currently-registered
        architecture is trained on the same 16kHz/4s convention). Default is
        a no-op passthrough. Override only if a future architecture
        genuinely needs different signal conditioning than the shared
        pipeline already applies — most won't."""
        return waveform

    @abstractmethod
    def predict(self, loaded_model: Any, feature: "ExtractedFeature") -> Any:
        """The architecture-specific forward pass. Returns whatever raw
        shape is natural here (a 2-logit softmax vector, a single sigmoid
        probability, ...) — convert_prediction() is what turns this into
        the shape every downstream module actually consumes."""

    @abstractmethod
    def convert_prediction(self, raw_prediction: Any) -> "InferenceResult":
        """Converts this architecture's raw predict() output into
        VoiceGuard's canonical InferenceResult: bonafide_score, spoof_score,
        label, inference_time_ms. `label` must always come out as
        'bonafide' or 'spoof' — this architecture's own native label
        vocabulary (e.g. 'Genuine'/'Deepfake') is translated here, using
        this adapter's own label_mapping, and never leaks past this point.
        api.inference.confidence.decide() specifically pattern-matches on
        the literal string 'bonafide'; every adapter's convert_prediction()
        is the one place responsible for producing that literal, regardless
        of what the underlying model actually calls its classes."""

    def supports_explainability(self) -> bool:
        return False

    def generate_explanation(
        self,
        loaded_model: Any,
        feature: "ExtractedFeature",
        inference_result: "InferenceResult",
        confidence_result: "ConfidenceResult",
        *,
        silence_ratio: float,
        model_version_label: str,
    ) -> "ExplanationResult":
        """Default implementation: explainability unavailable. Architectures
        that support it (see supports_explainability) override this method;
        api.inference.jobs calls generate_explanation() unconditionally for
        every architecture and never itself branches on
        supports_explainability — "not supported" is just another
        implementation of this same method, not a special case the
        orchestrator has to know about. The scan must never fail because
        explainability isn't available for a given architecture — hence a
        normal ExplanationResult (empty regions, a warning), not an
        exception."""
        from api.inference.explainability import ExplanationResult

        return ExplanationResult(
            salient_regions=[],
            notes=[],
            warnings=[f"Explainability is not available for the {self.architecture} architecture."],
            feature_extractor=f"{feature.name}:{feature.version}",
            model_version=model_version_label,
        )

    @abstractmethod
    def metadata(self) -> AdapterMetadata: ...
