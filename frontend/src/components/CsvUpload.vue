<template>
  <div class="csv-upload-container">
    <h4>Upload OHLCV CSV:</h4>
    <div class="file-input-container">
      <input
        type="file"
        id="csvFile"
        ref="csvFile"
        @change="handleFileSelect"
        accept=".csv"
        class="csv-upload-input"
        :disabled="isLoading"
      />
      <button
        @click="triggerFileUpload"
        class="csv-upload-button"
        :disabled="!selectedFile || isLoading"
      >
        {{ isLoading ? "Uploading..." : "Upload OHLCV" }}
      </button>
    </div>
    <p
      v-if="message"
      class="upload-message"
      :class="{
        'status-success': messageType === 'success',
        'status-error': messageType === 'error',
        'status-info': messageType === 'info',
      }"
    >
      {{ message }}
    </p>
  </div>
</template>

<script>
export default {
  name: "CsvUpload",
  data() {
    return {
      selectedFile: null,
      message: "",
      isLoading: false,
      messageType: "info",
      isValidFile: false,
    };
  },
  methods: {
    async handleFileSelect() {
      this.selectedFile = this.$refs.csvFile.files[0];
      this.message = "";
      this.messageType = "info";
      this.isValidFile = false;

      if (this.selectedFile) {
        this.message = `File selected: ${this.selectedFile.name}. Validating...`;
        try {
          const fileContent = await this.readFileContent(this.selectedFile);
          const header = fileContent.split(/\\r?\\n/)[0].toLowerCase();
          const requiredColumns = [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
          ];
          const missingColumns = requiredColumns.filter(
            (col) => !header.includes(col)
          );

          if (missingColumns.length > 0) {
            this.message = `CSV missing required columns: ${missingColumns.join(
              ", "
            )}. Expected: ${requiredColumns.join(", ")}`;
            this.messageType = "error";
            this.isValidFile = false;
            if (this.$refs.csvFile) {
              this.$refs.csvFile.value = null;
            }
            this.selectedFile = null;
          } else {
            this.message = `File ${this.selectedFile.name} is valid. Ready to upload.`;
            this.messageType = "info";
            this.isValidFile = true;
          }
        } catch (e) {
          this.message = "Error reading or validating file.";
          this.messageType = "error";
          this.isValidFile = false;
          if (this.$refs.csvFile) {
            this.$refs.csvFile.value = null;
          }
          this.selectedFile = null;
          console.error("Error during file validation:", e);
        }
      } else {
        this.isValidFile = false;
      }
    },
    readFileContent(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e);
        reader.readAsText(file);
      });
    },
    triggerFileUpload() {
      if (!this.selectedFile) {
        this.message = "Please select a file first.";
        this.messageType = "error";
        this.isValidFile = false;
        return;
      }
      if (!this.isValidFile) {
        if (!this.message || this.messageType !== "error") {
          this.message =
            "The selected file is not valid. Please check the format and headers.";
          this.messageType = "error";
        }
        return;
      }
      this.isLoading = true;
      this.message = "Uploading file...";
      this.messageType = "info";
      this.$emit("file-upload-initiated", this.selectedFile);
    },
    setUploadStatus(isLoading, message, messageType = "info") {
      this.isLoading = isLoading;
      this.message = message;
      this.messageType = messageType;
      if (!isLoading && messageType === "success") {
        if (this.$refs.csvFile) {
          this.$refs.csvFile.value = null;
        }
        this.selectedFile = null;
        this.isValidFile = false;
      } else if (!isLoading && messageType === "error") {
        // If backend reports error, we might want to reset isValidFile too,
        // though the file itself *was* valid enough to be sent.
        // For now, let's keep selectedFile so user doesn't have to re-select if it was a transient backend issue
        // but if the error is due to content, ideally it's caught client side.
        // We do clear the input if client-side validation fails earlier.
      }
    },
  },
};
</script>

<style scoped>
.csv-upload-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.csv-upload-container h4 {
  font-weight: bold;
  font-size: 1em;
  color: #333;
  margin: 0 0 5px 0;
}

.file-input-container {
  display: flex;
  gap: 10px;
  align-items: center;
  width: 100%;
}

.csv-upload-input {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9em;
  flex-grow: 1;
}

.csv-upload-button {
  padding: 8px 15px;
  background-color: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  min-width: 120px;
  text-align: center;
}

.csv-upload-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.csv-upload-button:hover:not(:disabled) {
  background-color: #45a049;
}

.upload-message {
  font-size: 0.9em;
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
  width: calc(100% - 16px);
  box-sizing: border-box;
}

.upload-message.status-success {
  background-color: #e6ffed;
  border-left: 5px solid #4caf50;
  color: #2e7d32;
}

.upload-message.status-error {
  background-color: #ffebee;
  border-left: 5px solid #f44336;
  color: #c62828;
  font-weight: bold;
}

.upload-message.status-info {
  background-color: #e3f2fd;
  border-left: 5px solid #2196f3;
  color: #1565c0;
}
</style>
