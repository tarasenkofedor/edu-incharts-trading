<template>
  <div v-if="isVisible" class="chart-status-popup" :class="`popup-${type}`">
    <p>{{ message }}</p>
    <button @click="dismiss" class="close-button">&times;</button>
  </div>
</template>

<script>
export default {
  name: "ChartStatusPopup",
  props: {
    initialMessage: String,
    initialType: {
      type: String,
      default: "info", // 'info', 'warning', 'error'
    },
    autoDismissDelay: {
      type: Number,
      default: 0, // 0 means no auto-dismiss
    },
  },
  data() {
    return {
      isVisible: false,
      message: "",
      type: "info",
      timerId: null,
    };
  },
  methods: {
    show(message, type = "info", temporary = false) {
      this.message = message;
      this.type = type;
      this.isVisible = true;

      if (this.timerId) {
        clearTimeout(this.timerId);
        this.timerId = null;
      }

      if (temporary && this.autoDismissDelay > 0) {
        this.timerId = setTimeout(() => {
          this.dismiss();
        }, this.autoDismissDelay);
      } else if (
        this.autoDismissDelay > 0 &&
        !temporary &&
        type !== "error" &&
        type !== "warning"
      ) {
        // Auto-dismiss for general info messages if not explicitly temporary but delay is set
        this.timerId = setTimeout(() => {
          this.dismiss();
        }, this.autoDismissDelay);
      }
    },
    dismiss() {
      this.isVisible = false;
      if (this.timerId) {
        clearTimeout(this.timerId);
        this.timerId = null;
      }
      this.$emit("dismissed");
    },
    hide() {
      // Alias for dismiss, can be called externally
      this.dismiss();
    },
  },
  mounted() {
    if (this.initialMessage) {
      this.show(this.initialMessage, this.initialType);
    }
  },
  beforeDestroy() {
    if (this.timerId) {
      clearTimeout(this.timerId);
    }
  },
};
</script>

<style scoped>
.chart-status-popup {
  position: fixed;
  bottom: 20px;
  left: 20px;
  padding: 10px 15px;
  border-radius: 5px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 250px;
  max-width: 400px;
}

.popup-info {
  background-color: #e0e0e0;
  border-left: 5px solid #757575;
  color: #333;
}

.popup-warning {
  background-color: #fff3e0;
  border-left: 5px solid #ff9800;
  color: #333;
}

.popup-error {
  background-color: #ffebee;
  border-left: 5px solid #f44336;
  color: #333;
}

.chart-status-popup p {
  margin: 0;
  margin-right: 15px;
  font-size: 0.9em;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.2em;
  cursor: pointer;
  color: #555;
  padding: 0 5px;
}
.close-button:hover {
  color: #000;
}
</style>
