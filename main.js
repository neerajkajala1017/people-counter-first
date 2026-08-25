
const state = {
    uploadedFilename: null,
    isUploading: false,
    isProcessing: false,
};

// ── DOM refs ──────────────────────────────────────────────────
const fileInput       = document.getElementById("file-input");
const uploadLabel     = document.getElementById("upload-label");
const fileNameChip    = document.getElementById("file-name-chip");
const btnProcess      = document.getElementById("btn-process");
const originalVideo   = document.getElementById("original-video");
const processedVideo  = document.getElementById("processed-video");
const originalPlaceholder  = document.getElementById("original-placeholder");
const processedPlaceholder = document.getElementById("processed-placeholder");
const processedBadge  = document.getElementById("processed-badge");
const progressWrap    = document.getElementById("progress-wrap");
const progressFill    = document.getElementById("progress-fill");
const progressLabel   = document.getElementById("progress-label");
const statCount       = document.getElementById("stat-count");
const statusPill      = document.getElementById("status-pill");
const spinner         = document.getElementById("spinner");
const toast           = document.getElementById("toast");
const errorBanner     = document.getElementById("error-banner");

function setStatus(mode){
    const labels = {ready: "Ready", processing: "Processing...", done: "Finished", error: "Error"}

    statusPill.className = `status-pill ${mode}`
    statusPill.innerHTML = `<span class="status-dot"></span>${labels[mode]}`;
}

function showToast(message, type="default"){
    toast.textContent = message;
    toast.className = `show ${type}`;
    setTimeout(() => { toast.className = ""; }, 3500);
}

function showError(message){
    errorBanner.textContent = message;
    errorBanner.classList.add("visible");
}

function clearError(){
    errorBanner.classList.remove("visible");
}

function setProcessingUI(active){
    spinner.classList.toggle("visible", active);
    btnProcess.disabled = active || !state.uploadedFilename;
    uploadLabel.style.pointerEvents = active ? "none" : "";
    uploadLabel.style.opacity = active ? ".45" : "";
    state.isProcessing = active;
}

function showVideo(el, placeholder, src){
    el.removeAttribute("src");
    el.load()
    el.src = src;
    el.load()
    el.classList.add("visible");
    placeholder.style.display = "none";
}

function setProgress(pct){
    progressFill.style.width = `${pct}%`;
    progressLabel.textContent = `${Math.round(pct)}%`;
}

fileInput.addEventListener("change", () =>{
    const file = fileInput.files[0];

    if(!file) return;

    clearError();

    state.uploadedFilename = null;
    btnProcess.disabled = true;
    processedBadge.classList.remove("visible");

    const objectUrl = URL.createObjectURL(file);
    showVideo(originalVideo, originalPlaceholder, objectUrl);

    fileNameChip.textContent = file.name;
    fileNameChip.classList.add("visible");

    uploadFile(file);
});

function uploadFile(file){
    if(state.isUploading) return;
    state.isUploading = true;
    setStatus("processing");

    progressWrap.classList.add("visible");
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload");

    xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) setProgress((e.loaded/e.total) * 100);
    })

    xhr.addEventListener("load", () =>{
        state.isUploading = false;
        progressWrap.classList.remove("visible");

        if(xhr.status === 200){
            const data =JSON.parse(xhr.responseText);
            state.uploadedFilename = data.filename;
            btnProcess.disabled = false;
            setStatus("ready");
            showToast("Video uploaded - ready to process.", "success");
        } else{
            handleUploadError(xhr);
        }
    });

    xhr.addEventListener("error", () => {
        state.isUploading = false;
        progressWrap.classList.remove("visible");
        handleUploadError(xhr);
    })

    xhr.send(formData);
}

function handleUploadError(xhr){
    let msg = "Upload Failed";
    try{ msg = JSON.parse(xhr.responseText).detail || msg; } catch{}
    showError(msg);
    setStatus("error");
    showToast(msg, "error");
}

btnProcess.addEventListener("click", async () => {
    if(!state.uploadedFilename || state.isProcessing) return;

    clearError();
    setProcessingUI(true);
    setStatus("processing");
    statCount.textContent = "-";

    try {
        const res = await fetch(`/process/${state.uploadedFilename}`, {method: "POST"});
        const data = await res.json();
        
        if(!res.ok) throw new Error(data.detail || "Processing failed.");

        showVideo(processedVideo, processedPlaceholder, data.processed_url);

        statCount.textContent = data.max_people;
        processedBadge.textContent = `${data.max_people} detected`;
        processedBadge.classList.add("visible");

        setStatus("done");
        showToast(`Done! Up to ${data.max_people} people detected.`, "success");
    } catch(err){
        showError(err.message);
        setStatus("error");
        showToast(err.message, "error");
    } finally {
        setProcessingUI(false);
    }
});