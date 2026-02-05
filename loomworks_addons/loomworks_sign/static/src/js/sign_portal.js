/**
 * Loomworks Sign - Portal Signing Interface
 * Handles signature capture, field completion, and document submission
 */

(function () {
    'use strict';

    // Wait for DOM ready
    document.addEventListener('DOMContentLoaded', function () {
        const signApp = new SignPortalApp();
        signApp.init();
    });

    class SignPortalApp {
        constructor() {
            this.signatureData = null;
            this.initialData = null;
            this.fieldValues = {};
            this.signatureCanvas = null;
            this.initialCanvas = null;
            this.signatureCtx = null;
            this.initialCtx = null;
            this.isDrawing = false;
        }

        init() {
            this.setupCanvases();
            this.setupEventListeners();
            this.setupFieldHandlers();
        }

        // Canvas Setup
        setupCanvases() {
            // Signature canvas
            this.signatureCanvas = document.getElementById('signature-canvas');
            if (this.signatureCanvas) {
                this.signatureCtx = this.signatureCanvas.getContext('2d');
                this.setupCanvas(this.signatureCanvas, this.signatureCtx);
            }

            // Initial canvas
            this.initialCanvas = document.getElementById('initial-canvas');
            if (this.initialCanvas) {
                this.initialCtx = this.initialCanvas.getContext('2d');
                this.setupCanvas(this.initialCanvas, this.initialCtx);
            }
        }

        setupCanvas(canvas, ctx) {
            // Set canvas size based on container
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;

            // Configure drawing context
            ctx.strokeStyle = '#000';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            // Drawing events
            canvas.addEventListener('mousedown', (e) => this.startDrawing(e, ctx));
            canvas.addEventListener('mousemove', (e) => this.draw(e, ctx));
            canvas.addEventListener('mouseup', () => this.stopDrawing());
            canvas.addEventListener('mouseout', () => this.stopDrawing());

            // Touch events for mobile
            canvas.addEventListener('touchstart', (e) => this.startDrawing(e, ctx));
            canvas.addEventListener('touchmove', (e) => this.draw(e, ctx));
            canvas.addEventListener('touchend', () => this.stopDrawing());
        }

        startDrawing(e, ctx) {
            this.isDrawing = true;
            const pos = this.getCanvasPosition(e, ctx.canvas);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
        }

        draw(e, ctx) {
            if (!this.isDrawing) return;
            e.preventDefault();
            const pos = this.getCanvasPosition(e, ctx.canvas);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        }

        stopDrawing() {
            this.isDrawing = false;
        }

        getCanvasPosition(e, canvas) {
            const rect = canvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {
                x: clientX - rect.left,
                y: clientY - rect.top
            };
        }

        clearCanvas(canvas, ctx) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        // Event Listeners
        setupEventListeners() {
            // Clear signature button
            const clearSignBtn = document.getElementById('btn-clear-signature');
            if (clearSignBtn) {
                clearSignBtn.addEventListener('click', () => {
                    this.clearCanvas(this.signatureCanvas, this.signatureCtx);
                });
            }

            // Clear initial button
            const clearInitialBtn = document.getElementById('btn-clear-initial');
            if (clearInitialBtn) {
                clearInitialBtn.addEventListener('click', () => {
                    this.clearCanvas(this.initialCanvas, this.initialCtx);
                });
            }

            // Adopt signature button
            const adoptSignBtn = document.getElementById('btn-adopt-signature');
            if (adoptSignBtn) {
                adoptSignBtn.addEventListener('click', () => this.adoptSignature());
            }

            // Adopt initial button
            const adoptInitialBtn = document.getElementById('btn-adopt-initial');
            if (adoptInitialBtn) {
                adoptInitialBtn.addEventListener('click', () => this.adoptInitial());
            }

            // Signature text input
            const signatureText = document.getElementById('signature-text');
            if (signatureText) {
                signatureText.addEventListener('input', (e) => {
                    const preview = document.getElementById('signature-text-preview');
                    if (preview) {
                        preview.textContent = e.target.value;
                    }
                });
            }

            // Signature upload
            const signatureUpload = document.getElementById('signature-upload');
            if (signatureUpload) {
                signatureUpload.addEventListener('change', (e) => this.handleSignatureUpload(e));
            }

            // Submit button
            const submitBtn = document.getElementById('btn-sign-submit');
            if (submitBtn) {
                submitBtn.addEventListener('click', () => this.submitDocument());
            }

            // Refuse button
            const refuseBtn = document.getElementById('btn-sign-refuse');
            if (refuseBtn) {
                refuseBtn.addEventListener('click', () => this.refuseToSign());
            }
        }

        // Field Handlers
        setupFieldHandlers() {
            // Track changes to form fields
            document.querySelectorAll('.o_sign_field input, .o_sign_field textarea').forEach(field => {
                field.addEventListener('change', (e) => {
                    const itemId = e.target.dataset.itemId;
                    if (itemId) {
                        this.fieldValues[itemId] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                    }
                });
            });
        }

        // Signature Actions
        adoptSignature() {
            // Check which tab is active
            const drawTab = document.getElementById('tab-draw');
            const typeTab = document.getElementById('tab-type');
            const uploadTab = document.getElementById('tab-upload');

            if (drawTab && drawTab.classList.contains('active')) {
                // Get signature from canvas
                this.signatureData = this.signatureCanvas.toDataURL('image/png');
            } else if (typeTab && typeTab.classList.contains('active')) {
                // Generate signature from text
                const text = document.getElementById('signature-text').value;
                if (text) {
                    this.signatureData = this.generateTextSignature(text);
                }
            } else if (uploadTab && uploadTab.classList.contains('active')) {
                // Get uploaded signature
                const preview = document.getElementById('signature-upload-preview');
                if (preview && preview.src) {
                    this.signatureData = preview.src;
                }
            }

            if (this.signatureData) {
                this.applySignatureToFields('signature');
                bootstrap.Modal.getInstance(document.getElementById('signatureModal')).hide();
            }
        }

        adoptInitial() {
            this.initialData = this.initialCanvas.toDataURL('image/png');
            if (this.initialData) {
                this.applySignatureToFields('initial');
                bootstrap.Modal.getInstance(document.getElementById('initialModal')).hide();
            }
        }

        generateTextSignature(text) {
            // Create a canvas to render the text signature
            const canvas = document.createElement('canvas');
            canvas.width = 400;
            canvas.height = 100;
            const ctx = canvas.getContext('2d');

            // White background
            ctx.fillStyle = '#fff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw text with cursive font
            ctx.fillStyle = '#000';
            ctx.font = '40px "Brush Script MT", cursive';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(text, canvas.width / 2, canvas.height / 2);

            return canvas.toDataURL('image/png');
        }

        applySignatureToFields(type) {
            const data = type === 'signature' ? this.signatureData : this.initialData;
            document.querySelectorAll(`.o_sign_field[data-type="${type}"]`).forEach(field => {
                const itemId = field.dataset.itemId;
                this.fieldValues[itemId] = data;

                // Update UI
                field.innerHTML = `<div class="o_sign_completed_signature"><img src="${data}" alt="${type}"/></div>`;
                field.classList.add('completed');
            });
        }

        handleSignatureUpload(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const preview = document.getElementById('signature-upload-preview');
                    if (preview) {
                        preview.src = event.target.result;
                        preview.style.display = 'block';
                    }
                };
                reader.readAsDataURL(file);
            }
        }

        // Validation
        validateFields() {
            let isValid = true;
            const errors = [];

            document.querySelectorAll('.o_sign_field[data-required="true"]').forEach(field => {
                const itemId = field.dataset.itemId;
                const type = field.dataset.type;

                if (!this.fieldValues[itemId]) {
                    isValid = false;
                    field.classList.add('validation-error');
                    errors.push(`Please complete the required ${type} field`);
                } else {
                    field.classList.remove('validation-error');
                }
            });

            if (!isValid) {
                alert('Please complete all required fields:\n\n' + errors.join('\n'));
            }

            return isValid;
        }

        // Submit Document
        async submitDocument() {
            if (!this.validateFields()) {
                return;
            }

            // Show loading state
            this.showLoading(true);

            // Collect all field values
            const fieldData = {};
            document.querySelectorAll('.o_sign_field').forEach(field => {
                const itemId = field.dataset.itemId;
                if (this.fieldValues[itemId]) {
                    fieldData[itemId] = this.fieldValues[itemId];
                }
            });

            try {
                // Get tokens from URL
                const pathParts = window.location.pathname.split('/');
                const requestToken = pathParts[2];
                const signerToken = pathParts[3];

                const response = await fetch('/sign/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        request_token: requestToken,
                        signer_token: signerToken,
                        field_values: fieldData,
                        csrf_token: this.getCsrfToken()
                    })
                });

                const result = await response.json();

                if (result.success) {
                    window.location.href = result.redirect_url || '/sign/complete';
                } else {
                    alert('Error submitting document: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Submit error:', error);
                alert('An error occurred while submitting the document. Please try again.');
            } finally {
                this.showLoading(false);
            }
        }

        // Refuse to Sign
        async refuseToSign() {
            const confirmed = confirm('Are you sure you want to refuse to sign this document? The sender will be notified.');
            if (!confirmed) return;

            this.showLoading(true);

            try {
                const pathParts = window.location.pathname.split('/');
                const requestToken = pathParts[2];
                const signerToken = pathParts[3];

                const response = await fetch('/sign/refuse', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        request_token: requestToken,
                        signer_token: signerToken,
                        csrf_token: this.getCsrfToken()
                    })
                });

                const result = await response.json();

                if (result.success) {
                    window.location.href = result.redirect_url || '/sign/refused';
                } else {
                    alert('Error: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Refuse error:', error);
                alert('An error occurred. Please try again.');
            } finally {
                this.showLoading(false);
            }
        }

        // Utilities
        showLoading(show) {
            let loader = document.querySelector('.o_sign_loading');
            if (show) {
                if (!loader) {
                    loader = document.createElement('div');
                    loader.className = 'o_sign_loading';
                    loader.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
                    document.body.appendChild(loader);
                }
                loader.style.display = 'flex';
            } else if (loader) {
                loader.style.display = 'none';
            }
        }

        getCsrfToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            return meta ? meta.getAttribute('content') : '';
        }
    }

    // Export for use in other modules
    window.SignPortalApp = SignPortalApp;
})();
