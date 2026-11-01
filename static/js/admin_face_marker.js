/**
 * Admin Face Placement & Try-On Pinning Tool
 * Allows the admin to visually mark an oval target on any clothing/model image
 * where the user's face will be pinned during virtual try-on.
 */

(function (window) {
    "use strict";

    class AdminFaceMarker {
        constructor() {
            this.modal = null;
            this.canvas = null;
            this.ctx = null;
            this.image = null;

            // Target Pin State (in original image coordinates)
            this.targetX = 150;
            this.targetY = 40;
            this.targetW = 90;
            this.targetH = 120;
            this.targetAngle = 0; // degrees

            // Canvas display mapping
            this.scale = 1.0;
            this.offsetX = 0;
            this.offsetY = 0;

            // Drag state
            this.isDragging = false;
            this.dragOffsetLocalX = 0;
            this.dragOffsetLocalY = 0;

            this.onSaveCallback = null;

            this._initDOM();
        }

        _initDOM() {
            if (document.getElementById("adminFaceMarkerModal")) {
                this.modal = document.getElementById("adminFaceMarkerModal");
                this.canvas = document.getElementById("adminFaceMarkerCanvas");
                this.ctx = this.canvas.getContext("2d");
                this._bindControls();
                return;
            }

            const modalHtml = `
            <div id="adminFaceMarkerModal" class="admin-marker-modal">
                <div class="admin-marker-dialog">
                    <div class="admin-marker-header">
                        <h3>🎯 Mark Model Face Placement (Oval Target Tool)</h3>
                        <button type="button" class="admin-marker-close-btn" id="adminMarkerClose" title="Close">&times;</button>
                    </div>

                    <div class="admin-marker-hint">
                        Drag and resize the <strong>cyan oval target</strong> directly over the model's face.
                        When any user tries on this outfit, their face will be <strong>pinned onto this exact oval location</strong>.
                    </div>

                    <div class="admin-marker-body">
                        <div class="admin-canvas-wrapper" id="adminCanvasWrapper">
                            <canvas id="adminFaceMarkerCanvas" width="650" height="440"></canvas>
                        </div>

                        <div class="admin-marker-controls">
                            <!-- Width Slider -->
                            <div class="marker-row">
                                <label>↔ Face Width:</label>
                                <input type="range" id="markerWidthSlider" class="marker-slider" min="30" max="300" step="1" value="90">
                                <span id="markerWidthVal" class="marker-val">90px</span>
                            </div>

                            <!-- Height Slider -->
                            <div class="marker-row">
                                <label>↕ Face Height:</label>
                                <input type="range" id="markerHeightSlider" class="marker-slider" min="40" max="380" step="1" value="120">
                                <span id="markerHeightVal" class="marker-val">120px</span>
                            </div>

                            <!-- Angle Slider -->
                            <div class="marker-row">
                                <label>🔄 Head Tilt / Angle:</label>
                                <input type="range" id="markerAngleSlider" class="marker-slider" min="-40" max="40" step="1" value="0">
                                <span id="markerAngleVal" class="marker-val">0°</span>
                                <button type="button" id="markerResetAngle" style="padding:4px 8px; font-size:11px; border-radius:6px; border:1px solid #ddd; background:#fff; cursor:pointer;">Reset</button>
                            </div>

                            <div style="font-size: 11px; color: #666; display: flex; justify-content: space-between; padding-top: 4px; border-top: 1px dashed #e2ded8;">
                                <span id="markerCoordsDisplay">📍 Target: X: 150px, Y: 40px</span>
                                <span>💡 Tip: Click &amp; drag the oval inside the viewer to position</span>
                            </div>
                        </div>

                        <div class="admin-marker-actions">
                            <button type="button" class="marker-btn-secondary" id="markerAutoDetectBtn" title="Auto-detect face in outfit">
                                🤖 Auto-Detect Model Face
                            </button>
                            <button type="button" class="marker-btn-primary" id="markerSaveBtn">
                                ✓ Set This Location as Try-On Face Pin
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;

            document.body.insertAdjacentHTML("beforeend", modalHtml);
            this.modal = document.getElementById("adminFaceMarkerModal");
            this.canvas = document.getElementById("adminFaceMarkerCanvas");
            this.ctx = this.canvas.getContext("2d");
            this._bindControls();
        }

        _bindControls() {
            const closeBtn = document.getElementById("adminMarkerClose");
            if (closeBtn) closeBtn.onclick = () => this.close();

            const wrapper = document.getElementById("adminCanvasWrapper");

            // Mouse drag
            wrapper.onmousedown = (e) => {
                const rect = this.canvas.getBoundingClientRect();
                const mouseCanvasX = e.clientX - rect.left;
                const mouseCanvasY = e.clientY - rect.top;

                // Convert to image coordinates
                const imgX = (mouseCanvasX - this.offsetX) / this.scale;
                const imgY = (mouseCanvasY - this.offsetY) / this.scale;

                // Center of oval target
                const cx = this.targetX + this.targetW / 2;
                const cy = this.targetY + this.targetH / 2;

                const dx = imgX - cx;
                const dy = imgY - cy;

                // Check if click is anywhere near the oval target
                const hitRadius = Math.max(this.targetW, this.targetH) * 0.75;
                if (Math.hypot(dx, dy) <= hitRadius) {
                    this.isDragging = true;
                    this.dragOffsetLocalX = imgX - this.targetX;
                    this.dragOffsetLocalY = imgY - this.targetY;
                }
            };

            window.addEventListener("mousemove", (e) => {
                if (!this.isDragging || !this.image) return;
                const rect = this.canvas.getBoundingClientRect();
                const mouseCanvasX = e.clientX - rect.left;
                const mouseCanvasY = e.clientY - rect.top;

                const imgX = (mouseCanvasX - this.offsetX) / this.scale;
                const imgY = (mouseCanvasY - this.offsetY) / this.scale;

                this.targetX = Math.round(Math.max(0, Math.min(this.image.width - this.targetW, imgX - this.dragOffsetLocalX)));
                this.targetY = Math.round(Math.max(0, Math.min(this.image.height - this.targetH, imgY - this.dragOffsetLocalY)));

                this._updateCoordsText();
                this.draw();
            });

            window.addEventListener("mouseup", () => {
                this.isDragging = false;
            });

            // Sliders
            const wSlider = document.getElementById("markerWidthSlider");
            if (wSlider) {
                wSlider.oninput = (e) => {
                    this.targetW = parseInt(e.target.value, 10);
                    const val = document.getElementById("markerWidthVal");
                    if (val) val.textContent = `${this.targetW}px`;
                    this._updateCoordsText();
                    this.draw();
                };
            }

            const hSlider = document.getElementById("markerHeightSlider");
            if (hSlider) {
                hSlider.oninput = (e) => {
                    this.targetH = parseInt(e.target.value, 10);
                    const val = document.getElementById("markerHeightVal");
                    if (val) val.textContent = `${this.targetH}px`;
                    this._updateCoordsText();
                    this.draw();
                };
            }

            const aSlider = document.getElementById("markerAngleSlider");
            if (aSlider) {
                aSlider.oninput = (e) => {
                    this.targetAngle = parseInt(e.target.value, 10);
                    const val = document.getElementById("markerAngleVal");
                    if (val) val.textContent = `${this.targetAngle}°`;
                    this._updateCoordsText();
                    this.draw();
                };
            }

            const rAngleBtn = document.getElementById("markerResetAngle");
            if (rAngleBtn) {
                rAngleBtn.onclick = () => {
                    this.targetAngle = 0;
                    if (aSlider) aSlider.value = 0;
                    const val = document.getElementById("markerAngleVal");
                    if (val) val.textContent = `0°`;
                    this._updateCoordsText();
                    this.draw();
                };
            }

            // Auto-detect button
            const autoBtn = document.getElementById("markerAutoDetectBtn");
            if (autoBtn) autoBtn.onclick = () => this.autoDetectModelFace();

            // Save button
            const saveBtn = document.getElementById("markerSaveBtn");
            if (saveBtn) saveBtn.onclick = () => this.savePin();
        }

        _updateCoordsText() {
            const display = document.getElementById("markerCoordsDisplay");
            if (display && this.image) {
                const normX = ((this.targetX / this.image.width) * 100).toFixed(1);
                const normY = ((this.targetY / this.image.height) * 100).toFixed(1);
                display.innerHTML = `📍 Target: X: ${this.targetX}px (${normX}%), Y: ${this.targetY}px (${normY}%), W: ${this.targetW}px, H: ${this.targetH}px`;
            }
        }

        openWithFile(file, existingTargetJson, onSaveCallback) {
            this.onSaveCallback = onSaveCallback;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.openWithUrl(e.target.result, existingTargetJson, onSaveCallback);
            };
            reader.readAsDataURL(file);
        }

        openWithUrl(imgUrl, existingTargetJson, onSaveCallback) {
            this.onSaveCallback = onSaveCallback;
            const img = new Image();
            img.onload = () => {
                this.image = img;
                this._initTargetState(existingTargetJson);
                this.modal.style.display = "flex";
                this.draw();

                // If no existing custom target was provided, trigger auto-detect
                if (!existingTargetJson) {
                    setTimeout(() => this.autoDetectModelFace(), 150);
                }
            };
            img.src = imgUrl;
        }

        close() {
            if (this.modal) this.modal.style.display = "none";
        }

        _initTargetState(existingTargetJson) {
            if (!this.image) return;

            let parsed = null;
            if (existingTargetJson) {
                try {
                    parsed = typeof existingTargetJson === "string" ? JSON.parse(existingTargetJson) : existingTargetJson;
                } catch (e) {
                    parsed = null;
                }
            }

            if (parsed && (parsed.x !== undefined || parsed.norm_x !== undefined)) {
                this.targetW = parsed.width || (parsed.norm_w ? Math.round(parsed.norm_w * this.image.width) : Math.round(this.image.width * 0.25));
                this.targetH = parsed.height || (parsed.norm_h ? Math.round(parsed.norm_h * this.image.height) : Math.round(this.targetW * 1.35));
                this.targetX = parsed.x !== undefined ? parsed.x : Math.round(parsed.norm_x * this.image.width);
                this.targetY = parsed.y !== undefined ? parsed.y : Math.round(parsed.norm_y * this.image.height);
                this.targetAngle = parsed.angle || 0;
            } else {
                // Default position in top center of garment
                this.targetW = Math.round(this.image.width * 0.28);
                this.targetH = Math.round(this.targetW * 1.32);
                this.targetX = Math.round((this.image.width - this.targetW) / 2);
                this.targetY = Math.round(this.image.height * 0.05);
                this.targetAngle = 0;
            }

            // Sync sliders
            const wSlider = document.getElementById("markerWidthSlider");
            if (wSlider) {
                wSlider.max = Math.max(300, Math.round(this.image.width * 0.8));
                wSlider.value = this.targetW;
            }
            const wVal = document.getElementById("markerWidthVal");
            if (wVal) wVal.textContent = `${this.targetW}px`;

            const hSlider = document.getElementById("markerHeightSlider");
            if (hSlider) {
                hSlider.max = Math.max(380, Math.round(this.image.height * 0.8));
                hSlider.value = this.targetH;
            }
            const hVal = document.getElementById("markerHeightVal");
            if (hVal) hVal.textContent = `${this.targetH}px`;

            const aSlider = document.getElementById("markerAngleSlider");
            if (aSlider) aSlider.value = this.targetAngle;
            const aVal = document.getElementById("markerAngleVal");
            if (aVal) aVal.textContent = `${this.targetAngle}°`;

            this._updateCoordsText();
        }

        draw() {
            if (!this.image || !this.ctx) return;

            const cw = this.canvas.width;
            const ch = this.canvas.height;

            this.ctx.clearRect(0, 0, cw, ch);

            // Compute scaling to fit clothing photo in canvas
            this.scale = Math.min(cw / this.image.width, ch / this.image.height);
            this.offsetX = (cw - this.image.width * this.scale) / 2;
            this.offsetY = (ch - this.image.height * this.scale) / 2;

            // 1. Draw base clothing photo
            this.ctx.drawImage(
                this.image,
                this.offsetX,
                this.offsetY,
                this.image.width * this.scale,
                this.image.height * this.scale
            );

            // 2. Map target oval to canvas coordinates
            const ovalCanvasX = this.offsetX + (this.targetX + this.targetW / 2) * this.scale;
            const ovalCanvasY = this.offsetY + (this.targetY + this.targetH / 2) * this.scale;
            const radiusX = (this.targetW / 2) * this.scale;
            const radiusY = (this.targetH / 2) * this.scale;

            this.ctx.save();
            this.ctx.translate(ovalCanvasX, ovalCanvasY);
            this.ctx.rotate((this.targetAngle * Math.PI) / 180);

            // Translucent inner fill
            this.ctx.beginPath();
            this.ctx.ellipse(0, 0, radiusX, radiusY, 0, 0, Math.PI * 2);
            this.ctx.fillStyle = "rgba(13, 130, 68, 0.22)"; // translucent green
            this.ctx.fill();

            // Glowing Outer Oval Border
            this.ctx.lineWidth = 3;
            this.ctx.strokeStyle = "#00e5ff"; // Bright cyan
            this.ctx.setLineDash([8, 5]);
            this.ctx.stroke();

            // Solid inner border
            this.ctx.lineWidth = 1.5;
            this.ctx.strokeStyle = "#ffffff";
            this.ctx.setLineDash([]);
            this.ctx.stroke();

            // Crosshair pin mark
            this.ctx.strokeStyle = "#00e5ff";
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.moveTo(-15, 0);
            this.ctx.lineTo(15, 0);
            this.ctx.moveTo(0, -15);
            this.ctx.lineTo(0, 15);
            this.ctx.stroke();

            // Floating Label
            this.ctx.fillStyle = "rgba(0, 0, 0, 0.85)";
            this.ctx.fillRect(-65, -radiusY - 26, 130, 22);
            this.ctx.strokeStyle = "#00e5ff";
            this.ctx.strokeRect(-65, -radiusY - 26, 130, 22);

            this.ctx.font = "bold 11px sans-serif";
            this.ctx.fillStyle = "#ffffff";
            this.ctx.textAlign = "center";
            this.ctx.fillText("📍 PIN USER FACE", 0, -radiusY - 11);

            this.ctx.restore();
        }

        async autoDetectModelFace() {
            if (!this.image) return;

            const autoBtn = document.getElementById("markerAutoDetectBtn");
            const orig = autoBtn.innerHTML;
            autoBtn.innerHTML = "⏳ Detecting...";

            try {
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
                    body: JSON.stringify({ image_data: dataUrl })
                });

                const data = await res.json();
                if (data.success && data.face) {
                    const f = data.face;
                    this.targetX = Math.round(f.x / scale);
                    this.targetY = Math.round(f.y / scale);
                    this.targetW = Math.round(f.width / scale);
                    this.targetH = Math.round((f.height / scale) * 1.15); // slight vertical margin for chin
                    this.targetAngle = 0;

                    // Sync sliders
                    const wSlider = document.getElementById("markerWidthSlider");
                    if (wSlider) wSlider.value = this.targetW;
                    const wVal = document.getElementById("markerWidthVal");
                    if (wVal) wVal.textContent = `${this.targetW}px`;

                    const hSlider = document.getElementById("markerHeightSlider");
                    if (hSlider) hSlider.value = this.targetH;
                    const hVal = document.getElementById("markerHeightVal");
                    if (hVal) hVal.textContent = `${this.targetH}px`;

                    this._updateCoordsText();
                    this.draw();
                } else {
                    alert("Could not automatically detect a model face. You can drag and adjust the cyan oval manually.");
                }
            } catch (err) {
                console.warn("[Admin Face Marker] Auto-detect error:", err);
            } finally {
                autoBtn.innerHTML = orig;
            }
        }

        savePin() {
            if (!this.image) return;

            const targetData = {
                x: this.targetX,
                y: this.targetY,
                width: this.targetW,
                height: this.targetH,
                norm_x: parseFloat((this.targetX / this.image.width).toFixed(4)),
                norm_y: parseFloat((this.targetY / this.image.height).toFixed(4)),
                norm_w: parseFloat((this.targetW / this.image.width).toFixed(4)),
                norm_h: parseFloat((this.targetH / this.image.height).toFixed(4)),
                angle: this.targetAngle,
                img_w: this.image.width,
                img_h: this.image.height
            };

            const jsonStr = JSON.stringify(targetData);

            this.close();

            if (typeof this.onSaveCallback === "function") {
                this.onSaveCallback(targetData, jsonStr);
            }
        }
    }

    window.AdminFaceMarker = new AdminFaceMarker();

})(window);

