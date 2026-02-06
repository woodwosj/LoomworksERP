/** @loomworks-module **/
/**
 * Loomworks Field Service Signature Pad Component
 * Provides touch-friendly signature capture for customer sign-off
 */

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FsmSignaturePad extends Component {
    static template = "loomworks_fsm.FsmSignaturePad";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");

        this.canvasRef = useRef("canvas");

        this.state = useState({
            isEmpty: true,
            isDrawing: false,
        });

        this.ctx = null;
        this.lastX = 0;
        this.lastY = 0;

        onMounted(() => {
            this.initCanvas();
            this.loadExistingSignature();
        });

        onWillUnmount(() => {
            this.removeEventListeners();
        });
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get readonly() {
        return this.props.readonly;
    }

    get containerClass() {
        const classes = ['o_fsm_signature_pad'];
        if (!this.state.isEmpty || this.value) {
            classes.push('is-signed');
        }
        if (this.readonly) {
            classes.push('readonly');
        }
        return classes.join(' ');
    }

    initCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        // Set canvas size
        const rect = canvas.parentElement.getBoundingClientRect();
        canvas.width = rect.width || 400;
        canvas.height = 200;

        // Get drawing context
        this.ctx = canvas.getContext('2d');
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 2;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        // Add event listeners
        this.addEventListeners();
    }

    addEventListeners() {
        const canvas = this.canvasRef.el;
        if (!canvas || this.readonly) return;

        // Mouse events
        canvas.addEventListener('mousedown', this.onStartDraw.bind(this));
        canvas.addEventListener('mousemove', this.onDraw.bind(this));
        canvas.addEventListener('mouseup', this.onEndDraw.bind(this));
        canvas.addEventListener('mouseout', this.onEndDraw.bind(this));

        // Touch events
        canvas.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: false });
        canvas.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
        canvas.addEventListener('touchend', this.onEndDraw.bind(this));
    }

    removeEventListeners() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        canvas.removeEventListener('mousedown', this.onStartDraw);
        canvas.removeEventListener('mousemove', this.onDraw);
        canvas.removeEventListener('mouseup', this.onEndDraw);
        canvas.removeEventListener('mouseout', this.onEndDraw);
        canvas.removeEventListener('touchstart', this.onTouchStart);
        canvas.removeEventListener('touchmove', this.onTouchMove);
        canvas.removeEventListener('touchend', this.onEndDraw);
    }

    loadExistingSignature() {
        if (this.value) {
            const img = new Image();
            img.onload = () => {
                if (this.ctx) {
                    this.ctx.drawImage(img, 0, 0);
                    this.state.isEmpty = false;
                }
            };
            // Value is base64 encoded
            img.src = `data:image/png;base64,${this.value}`;
        }
    }

    getCanvasCoordinates(event) {
        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();

        let clientX, clientY;
        if (event.touches && event.touches.length > 0) {
            clientX = event.touches[0].clientX;
            clientY = event.touches[0].clientY;
        } else {
            clientX = event.clientX;
            clientY = event.clientY;
        }

        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY
        };
    }

    onStartDraw(event) {
        if (this.readonly) return;

        this.state.isDrawing = true;
        const coords = this.getCanvasCoordinates(event);
        this.lastX = coords.x;
        this.lastY = coords.y;
    }

    onTouchStart(event) {
        event.preventDefault();
        this.onStartDraw(event);
    }

    onDraw(event) {
        if (!this.state.isDrawing || this.readonly) return;

        const coords = this.getCanvasCoordinates(event);

        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(coords.x, coords.y);
        this.ctx.stroke();

        this.lastX = coords.x;
        this.lastY = coords.y;
        this.state.isEmpty = false;
    }

    onTouchMove(event) {
        event.preventDefault();
        this.onDraw(event);
    }

    onEndDraw() {
        this.state.isDrawing = false;
    }

    onClearClick() {
        if (this.readonly) return;

        const canvas = this.canvasRef.el;
        if (this.ctx && canvas) {
            this.ctx.clearRect(0, 0, canvas.width, canvas.height);
            this.state.isEmpty = true;
        }
    }

    async onSaveClick() {
        if (this.readonly || this.state.isEmpty) return;

        const canvas = this.canvasRef.el;
        if (!canvas) return;

        try {
            // Convert canvas to base64 (without the data:image/png;base64, prefix)
            const dataUrl = canvas.toDataURL('image/png');
            const base64Data = dataUrl.replace(/^data:image\/png;base64,/, '');

            // Update the field value
            await this.props.record.update({ [this.props.name]: base64Data });

            this.notification.add("Signature saved", { type: "success" });
        } catch (error) {
            this.notification.add("Failed to save signature: " + error.message, { type: "danger" });
        }
    }

    get showPlaceholder() {
        return this.state.isEmpty && !this.value && !this.readonly;
    }

    get showActions() {
        return !this.readonly;
    }
}

// Register the widget
registry.category("fields").add("fsm_signature", {
    component: FsmSignaturePad,
    supportedTypes: ["binary"],
    extractProps: ({ attrs }) => ({
        readonly: attrs.readonly,
    }),
});
