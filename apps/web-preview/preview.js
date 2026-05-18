function classifyPreviewState(metadata) {
  if (!metadata || typeof metadata !== "object") {
    return { state: "missing", title: "No metadata loaded", message: "Paste preview metadata to classify the bundle." };
  }

  const classification = metadata.classification;
  if (classification === "demo_fixture") {
    return {
      state: "demo",
      title: "Demo fixture",
      message: "Local wiring is available, but this is not a real Cubism export.",
    };
  }

  if (classification === "real_cubism_export_validated") {
    return {
      state: "invalid",
      title: "Runtime smoke required",
      message: "Bundle validation alone is not accepted as real success. Run runtime smoke and require real_runtime_loaded.",
    };
  }

  if (classification === "contract_bundle_shape_validated") {
    return {
      state: "invalid",
      title: "Bundle shape only",
      message: "Files resolve, but independent real Cubism/runtime verification is missing. This is not a real export.",
    };
  }

  if (classification === "real_runtime_loaded") {
    return {
      state: "loaded",
      title: "Runtime loaded",
      message: "The runtime smoke path reported a successful model load.",
    };
  }

  if (classification === "real_cubism_export_attempted") {
    return {
      state: "invalid",
      title: "Real export attempted but invalid",
      message: "Official automation ran or was requested, but validation did not pass.",
    };
  }

  return { state: "invalid", title: "Invalid metadata", message: "Capability classification is missing or unknown." };
}

function bindPreviewUi() {
  const button = document.getElementById("classify");
  if (!button) return;
  button.addEventListener("click", () => {
    const raw = document.getElementById("metadata").value;
    let metadata;
    try {
      metadata = JSON.parse(raw);
    } catch (error) {
      metadata = null;
    }
    const result = classifyPreviewState(metadata);
    document.getElementById("state-title").textContent = result.title;
    document.getElementById("state-message").textContent = result.message;
    document.getElementById("capability").textContent = metadata?.classification || "unknown";
    document.getElementById("model-path").textContent = metadata?.model3_path || "n/a";
  });
}

if (typeof window !== "undefined") {
  window.classifyPreviewState = classifyPreviewState;
  window.addEventListener("DOMContentLoaded", bindPreviewUi);
}

if (typeof module !== "undefined") {
  module.exports = { classifyPreviewState };
}
