/**
 * Oval Face Cropper & Template Staging Engine
 * Provides interactive oval framing, auto face detection, and seamless server synchronization.
 */

(function (window) {
    "use strict";

    class OvalFaceCropper {
        constructor() {
            this.modal = null;
            this.canvas = null;
            this.ctx = null;
            this.image = null;
            this.rawFile = null;

            // Transform state
            this.zoom = 1.0;
            this.panX = 0;
            this.panY = 0;
            this.rotation = 0; // degrees
            this.aspectRatio = 1.35; // height / width

            // Interaction state
            this.isDragging = false;
            this.dragStartX = 0;
            this.dragStartY = 0;

            // Callback on successful save
            this.onSuccess = null;

            this._initDOM();
        }

        _initDOM() {
            if (document.getElementById("ovalCropperModal")) {
                this.modal = document.getElementById("ovalCropperModal");
                this.canvas = document.getElementById("ovalCropperCanvas");
                this.ctx = this.canvas.getContext("2d");
                this._bindControls();
                return;
            }

            const modalHtml = `
            <div id="ovalCropperModal" class="oval-cropper-modal">
                <div class="oval-cropper-dialog">
                    <div class="oval-cropper-header">
                        <h3>✨ Oval Face Template Cropper</h3>
                        <button type="button" class="oval-cropper-close-btn" id="ovalCropperClose" title="Close">&times;</button>
                    </div>

                    <div class="oval-cropper-hint">
                        Position and scale your face so it fits comfortably inside the <strong>oval guide</strong>.
                        Only your face within this oval will be applied across all clothing try-ons.
                    </div>

                    <div class="oval-cropper-body">
                        <div class="oval-canvas-container" id="ovalCanvasContainer">
                            <canvas id="ovalCropperCanvas" width="520" height="400"></canvas>
                        </div>

                        <div class="oval-cropper-toolbar">
                            <!-- Zoom Control -->
                            <div class="cropper-control-row">
                                <label>🔍 Zoom:</label>
                                <input type="range" id="cropperZoomSlider" class="cropper-slider" min="0.4" max="3.5" step="0.05" value="1.0">
                                <span id="cropperZoomVal" style="font-weight:700; width:45px;">100%</span>
                            </div>

                            <!-- Rotate Control -->
                            <div class="cropper-control-row">
                                <label>🔄 Tilt Angle:</label>
                                <input type="range" id="cropperRotateSlider" class="cropper-slider" min="-30" max="30" step="1" value="0">
                                <span id="cropperRotateVal" style="font-weight:700; width:45px;">0°</span>
                                <button type="button" id="cropperResetRotate" style="padding:4px 8px; font-size:11px; border-radius:6px; border:1px solid #ddd; background:#fff; cursor:pointer;">Reset</button>
                            </div>

                            <!-- Oval Shape Presets -->
                            <div class="cropper-control-row">
                                <label>📐 Face Shape:</label>
                                <div class="cropper-shape-pills">
                                    <button type="button" class="cropper-pill active" data-ratio="1.35">Classic Oval</button>
                                    <button type="button" class="cropper-pill" data-ratio="1.50">Long / Slim</button>
                                    <button type="button" class="cropper-pill" data-ratio="1.20">Round Face</button>
                                </div>
                            </div>
                        </div>

                        <div class="cropper-actions">
                            <button type="button" class="cropper-btn-secondary" id="cropperAutoDetectBtn" title="Automatically align oval over detected face">
                                🤖 Auto-Fit Face
                            </button>
                            <button type="button" class="cropper-btn-primary" id="cropperSaveBtn">
                                ✂ Crop &amp; Save Face Template
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;

            document.body.insertAdjacentHTML("beforeend", modalHtml);
            this.modal = document.getElementById("ovalCropperModal");
            this.canvas = document.getElementById("ovalCropperCanvas");
            this.ctx = this.canvas.getContext("2d");
            this._bindControls();
        }

        _bindControls() {
            const closeBtn = document.getElementById("ovalCropperClose");
            if (closeBtn) closeBtn.onclick = () => this.close();

            const container = document.getElementById("ovalCanvasContainer");

            // Mouse events
            container.onmousedown = (e) => {
                this.isDragging = true;
                this.dragStartX = e.clientX - this.panX;
                this.dragStartY = e.clientY - this.panY;
            };

            window.addEventListener("mousemove", (e) => {
                if (!this.isDragging) return;
                this.panX = e.clientX - this.dragStartX;
                this.panY = e.clientY - this.dragStartY;
                this.draw();
            });

            window.addEventListener("mouseup", () => {
                this.isDragging = false;
            });

            // Touch events
            container.ontouchstart = (e) => {
                if (e.touches.length === 1) {
                    this.isDragging = true;
                    this.dragStartX = e.touches[0].clientX - this.panX;
                    this.dragStartY = e.touches[0].clientY - this.panY;
                }
            };

            container.ontouchmove = (e) => {
                if (!this.isDragging || e.touches.length !== 1) return;
                e.preventDefault();
                this.panX = e.touches[0].clientX - this.dragStartX;
                this.panY = e.touches[0].clientY - this.dragStartY;
                this.draw();
            };

            container.ontouchend = () => {
                this.isDragging = false;
            };

            // Wheel zoom
            container.onwheel = (e) => {
                e.preventDefault();
                const delta = e.deltaY < 0 ? 0.08 : -0.08;
                this.zoom = Math.max(0.4, Math.min(3.5, this.zoom + delta));
                const slider = document.getElementById("cropperZoomSlider");
                if (slider) slider.value = this.zoom;
                const valText = document.getElementById("cropperZoomVal");
                if (valText) valText.textContent = `${Math.round(this.zoom * 100)}%`;
                this.draw();
            };

            // Slider zoom
            const zoomSlider = document.getElementById("cropperZoomSlider");
            if (zoomSlider) {
                zoomSlider.oninput = (e) => {
                    this.zoom = parseFloat(e.target.value);
                    const valText = document.getElementById("cropperZoomVal");
                    if (valText) valText.textContent = `${Math.round(this.zoom * 100)}%`;
                    this.draw();
                };
            }

            // Rotate slider
            const rotateSlider = document.getElementById("cropperRotateSlider");
            if (rotateSlider) {
                rotateSlider.oninput = (e) => {
                    this.rotation = parseFloat(e.target.value);
                    const valText = document.getElementById("cropperRotateVal");
                    if (valText) valText.textContent = `${this.rotation}°`;
                    this.draw();
                };
            }

            const resetRotateBtn = document.getElementById("cropperResetRotate");
            if (resetRotateBtn) {
                resetRotateBtn.onclick = () => {
                    this.rotation = 0;
                    if (rotateSlider) rotateSlider.value = 0;
                    const valText = document.getElementById("cropperRotateVal");
                    if (valText) valText.textContent = `0°`;
                    this.draw();
                };
            }

            // Shape pills
            const pills = document.querySelectorAll(".cropper-pill");
            pills.forEach((pill) => {
                pill.onclick = () => {
                    pills.forEach((p) => p.classList.remove("active"));
                    pill.classList.add("active");
                    this.aspectRatio = parseFloat(pill.dataset.ratio) || 1.35;
                    this.draw();
                };
            });

            // Auto-detect button
            const autoBtn = document.getElementById("cropperAutoDetectBtn");
            if (autoBtn) autoBtn.onclick = () => this.autoDetectFace();

            // Save button
            const saveBtn = document.getElementById("cropperSaveBtn");
            if (saveBtn) saveBtn.onclick = () => this.cropAndSave();
        }

        openWithFile(file, onSuccessCallback) {
            this.rawFile = file;
            this.onSuccess = onSuccessCallback;

            const reader = new FileReader();
            reader.onload = (e) => {
                this.openWithUrl(e.target.result, onSuccessCallback);
            };
            reader.readAsDataURL(file);
        }

        openWithUrl(dataUrl, onSuccessCallback) {
            this.onSuccess = onSuccessCallback;
            const img = new Image();
            img.onload = () => {
                this.image = img;
                this._resetState();
                this.modal.style.display = "flex";
                this.draw();

                // Trigger quick automatic face centering
                setTimeout(() => this.autoDetectFace(), 200);
            };
            img.src = dataUrl;
        }

        close() {
            if (this.modal) this.modal.style.display = "none";
        }

        _resetState() {
            this.zoom = 1.0;
            this.panX = 0;
            this.panY = 0;
            this.rotation = 0;
            this.aspectRatio = 1.35;

            const zoomSlider = document.getElementById("cropperZoomSlider");
            if (zoomSlider) zoomSlider.value = 1.0;
            const zoomVal = document.getElementById("cropperZoomVal");
            if (zoomVal) zoomVal.textContent = "100%";

            const rotSlider = document.getElementById("cropperRotateSlider");
            if (rotSlider) rotSlider.value = 0;
            const rotVal = document.getElementById("cropperRotateVal");
            if (rotVal) rotVal.textContent = "0°";
        }

        getOvalParams() {
            const cw = this.canvas.width;
            const ch = this.canvas.height;
            const cx = cw / 2;
            const cy = ch / 2;

            // Compute radius so oval comfortably fits inside canvas
            const maxRadiusY = ch * 0.42;
            const radiusY = maxRadiusY;
            const radiusX = radiusY / this.aspectRatio;

            return { cx, cy, radiusX, radiusY };
        }

        draw() {
            if (!this.image || !this.ctx) return;

            const cw = this.canvas.width;
            const ch = this.canvas.height;
            const { cx, cy, radiusX, radiusY } = this.getOvalParams();

            this.ctx.clearRect(0, 0, cw, ch);

            // 1. Draw Image with pan, zoom, rotation around canvas center
            this.ctx.save();
            this.ctx.translate(cx + this.panX, cy + this.panY);
            this.ctx.rotate((this.rotation * Math.PI) / 180);
            this.ctx.scale(this.zoom, this.zoom);

            const imgW = this.image.width;
            const imgH = this.image.height;
            // Fit image base scale
            const baseScale = Math.min((cw * 0.85) / imgW, (ch * 0.85) / imgH);
            const renderW = imgW * baseScale;
            const renderH = imgH * baseScale;

            this.ctx.drawImage(this.image, -renderW / 2, -renderH / 2, renderW, renderH);
            this.ctx.restore();

            // 2. Draw Translucent Dark Vignette outside the Oval
            this.ctx.save();
            this.ctx.beginPath();
            // Outer rectangle
            this.ctx.rect(0, 0, cw, ch);
            // Inner oval cutout (clockwise outer, counter-clockwise inner for evenodd)
            this.ctx.ellipse(cx, cy, radiusX, radiusY, 0, 0, Math.PI * 2, true);
            this.ctx.fillStyle = "rgba(10, 10, 10, 0.68)";
            this.ctx.fill();
            this.ctx.restore();

            // 3. Draw Stylized Oval Guide Border
            this.ctx.save();
            this.ctx.beginPath();
            this.ctx.ellipse(cx, cy, radiusX, radiusY, 0, 0, Math.PI * 2);
            this.ctx.strokeStyle = "#e8b87d"; // Warm gold border
            this.ctx.lineWidth = 2.5;
            this.ctx.setLineDash([7, 5]);
            this.ctx.stroke();

            // Subtle outer glow
            this.ctx.strokeStyle = "rgba(255, 255, 255, 0.5)";
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash([]);
            this.ctx.stroke();
            this.ctx.restore();

            // 4. Subtle Landmark Guides (Eye Level & Chin Level)
            this.ctx.save();
            this.ctx.strokeStyle = "rgba(232, 184, 125, 0.35)";
            this.ctx.lineWidth = 1;
            this.ctx.setLineDash([4, 4]);

            // Eye line (at ~40% of oval height)
            const eyeY = cy - radiusY * 0.20;
            const eyeSpan = radiusX * 0.85;
            this.ctx.beginPath();
            this.ctx.moveTo(cx - eyeSpan, eyeY);
            this.ctx.lineTo(cx + eyeSpan, eyeY);
            this.ctx.stroke();

            // Chin line (at ~88% of oval height)
            const chinY = cy + radiusY * 0.78;
            const chinSpan = radiusX * 0.45;
            this.ctx.beginPath();
            this.ctx.moveTo(cx - chinSpan, chinY);
            this.ctx.lineTo(cx + chinSpan, chinY);
            this.ctx.stroke();

            // Vertical center line
            this.ctx.beginPath();
            this.ctx.moveTo(cx, cy - radiusY * 0.95);
            this.ctx.lineTo(cx, cy + radiusY * 0.95);
            this.ctx.stroke();

            // Helper text inside oval
            this.ctx.font = "600 11px sans-serif";
            this.ctx.fillStyle = "rgba(255, 255, 255, 0.75)";
            this.ctx.textAlign = "center";
            this.ctx.fillText("👀 Eye Level", cx, eyeY - 6);
            this.ctx.fillText("Chin", cx, chinY + 14);

            this.ctx.restore();
        }

        async autoDetectFace() {
            if (!this.image) return;

            const autoBtn = document.getElementById("cropperAutoDetectBtn");
            const originalText = autoBtn ? autoBtn.innerHTML : "";
            if (autoBtn) autoBtn.innerHTML = "⏳ Detecting...";

            try {
                // Prepare small snapshot for fast server face detection
                const off = document.createElement("canvas");
                const scale = Math.min(1.0, 800 / Math.max(this.image.width, this.image.height));
                off.width = Math.round(this.image.width * scale);
                off.height = Math.round(this.image.height * scale);
                const octx = off.getContext("2d");
                octx.drawImage(this.image, 0, 0, off.width, off.height);
                const dataUrl = off.toDataURL("image/jpeg", 0.85);

                const res = await fetch("/detect-face-bounds", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ image_data: dataUrl }),
                });

                const data = await res.json();
                if (data.success && data.face) {
                    const f = data.face;
                    // Map back to original image space
                    const origX = f.x / scale;
                    const origY = f.y / scale;
                    const origW = f.width / scale;
                    const origH = f.height / scale;

                    const cw = this.canvas.width;
                    const ch = this.canvas.height;
                    const { cx, cy, radiusX, radiusY } = this.getOvalParams();

                    // Calculate base scale
                    const baseScale = Math.min((cw * 0.85) / this.image.width, (ch * 0.85) / this.image.height);
                    const faceCenterX = (origX + origW / 2 - this.image.width / 2) * baseScale;
                    const faceCenterY = (origY + origH / 2 - this.image.height / 2) * baseScale;

                    // Match face dimensions to oval dimensions (zoom so face width ~ 85% of oval width)
                    const targetZoom = ((radiusX * 2 * 0.90) / (origW * baseScale));
                    this.zoom = Math.max(0.5, Math.min(3.0, targetZoom));

                    this.panX = -faceCenterX * this.zoom;
                    // Slightly offset chin to meet bottom oval boundary
                    this.panY = -faceCenterY * this.zoom - (radiusY * 0.05);
                    this.rotation = 0;

                    const zoomSlider = document.getElementById("cropperZoomSlider");
                    if (zoomSlider) zoomSlider.value = this.zoom;
                    const zoomVal = document.getElementById("cropperZoomVal");
                    if (zoomVal) zoomVal.textContent = `${Math.round(this.zoom * 100)}%`;

                    this.draw();
                } else {
                    console.log("[Oval Cropper] Face auto-detection note:", data.message || "Manual adjustment recommended");
                }
            } catch (err) {
                console.warn("[Oval Cropper] Auto-detect error:", err);
            } finally {
                if (autoBtn) autoBtn.innerHTML = originalText;
            }
        }

        async cropAndSave() {
            if (!this.image) return;

            const saveBtn = document.getElementById("cropperSaveBtn");
            const origText = saveBtn.innerHTML;
            saveBtn.innerHTML = "⏳ Saving Face Template...";
            saveBtn.disabled = true;

            try {
                const { cx, cy, radiusX, radiusY } = this.getOvalParams();

                // High-resolution export canvas for crisp try-on face template (width 600px, height ~810px)
                const outW = 600;
                const outH = Math.round(outW * this.aspectRatio);
                const out = document.createElement("canvas");
                out.width = outW;
                out.height = outH;
                const octx = out.getContext("2d");

                const scaleFactor = outW / (radiusX * 2);

                // 1. Create feathered elliptical clip on output canvas
                octx.save();
                octx.beginPath();
                octx.ellipse(outW / 2, outH / 2, outW / 2 - 2, outH / 2 - 2, 0, 0, Math.PI * 2);
                octx.clip();

                // 2. Map coordinates from display canvas to output canvas
                octx.translate(outW / 2, outH / 2);
                octx.rotate((this.rotation * Math.PI) / 180);
                octx.scale(this.zoom * scaleFactor, this.zoom * scaleFactor);

                const cw = this.canvas.width;
                const ch = this.canvas.height;
                const baseScale = Math.min((cw * 0.85) / this.image.width, (ch * 0.85) / this.image.height);
                const renderW = this.image.width * baseScale;
                const renderH = this.image.height * baseScale;

                // Adjust for pan offset
                const panOffsetX = this.panX / this.zoom;
                const panOffsetY = this.panY / this.zoom;

                octx.drawImage(
                    this.image,
                    -renderW / 2 + panOffsetX,
                    -renderH / 2 + panOffsetY,
                    renderW,
                    renderH
                );
                octx.restore();

                const croppedDataUrl = out.toDataURL("image/png");

                // Submit to backend
                const response = await fetch("/save-face-template", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        image_data: croppedDataUrl,
                        meta: {
                            zoom: this.zoom,
                            rotation: this.rotation,
                            aspectRatio: this.aspectRatio
                        }
                    })
                });

                const result = await response.json();

                if (result.success) {
                    this.close();

                    if (typeof this.onSuccess === "function") {
                        this.onSuccess(result);
                    } else {
                        // Default toast / reload or update avatar
                        window.location.reload();
                    }
                } else {
                    alert(result.error || "Could not save face template. Please ensure your face is inside the oval.");
                }
            } catch (err) {
                alert("An error occurred while saving your face template: " + err.message);
            } finally {
                saveBtn.innerHTML = origText;
                saveBtn.disabled = false;
            }
        }
    }

    // Attach to global scope
    window.OvalFaceCropper = new OvalFaceCropper();

})(window);

