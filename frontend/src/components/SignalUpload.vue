<template>
  <div class="signal-upload-container">
    <h4>Upload Signal CSV:</h4>
    <div class="file-input-container">
      <input
        type="file"
        @change="handleFileChange"
        accept=".csv"
        ref="fileInputSignal"
        :disabled="isLoading"
      />
      <button @click="handleUpload" :disabled="!selectedFile || isLoading">
        {{ isLoading ? "Processing..." : "Upload Signals" }}
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
  name: "SignalUpload",
  data() {
    return {
      selectedFile: null,
      isLoading: false,
      message: "",
      messageType: "info", // 'info', 'success', 'error'
      isValidFile: false, // Added for client-side validation status
    };
  },
  methods: {
    async handleFileChange(event) {
      this.selectedFile = event.target.files[0];
      this.message = "";
      this.messageType = "info";
      this.isValidFile = false;

      if (this.selectedFile) {
        this.message = `File selected: ${this.selectedFile.name}. Validating headers...`;
        try {
          await this.validateSignalCsvHeaders(this.selectedFile);
          // If validateSignalCsvHeaders doesn't throw, it means headers are fine (or it set isValidFile to true)
          if (this.isValidFile) {
            // Check the flag set by the validator
            this.message = `File ${this.selectedFile.name} headers are valid. Ready to process.`;
            this.messageType = "info";
          }
          // Error message and isValidFile = false should be handled within validateSignalCsvHeaders
        } catch (validationError) {
          // This catch block might be redundant if validateSignalCsvHeaders handles its own errors
          // and sets message/messageType directly, but kept for safety.
          this.message = validationError.message || "Header validation failed.";
          this.messageType = "error";
          this.isValidFile = false;
          if (this.$refs.fileInputSignal) {
            this.$refs.fileInputSignal.value = null;
          }
          this.selectedFile = null;
        }
      } else {
        this.isValidFile = false; // No file selected
      }
    },
    readFileContent(file) {
      // Helper to read file content
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e);
        reader.readAsText(file);
      });
    },
    async validateSignalCsvHeaders(file) {
      // This method will now only validate headers and set isValidFile and messages.
      // It will throw an error or directly set error messages for handleFileChange to catch/reflect.
      try {
        const fileContent = await this.readFileContent(file);
        const lines = fileContent.split(/\\r?\\n/).map((line) => line.trim());
        if (lines.length === 0 || lines[0].trim() === "") {
          this.message = "CSV file is empty or has no header row.";
          this.messageType = "error";
          this.isValidFile = false;
          return; // Or throw new Error(...)
        }
        const header = lines[0].split(",").map((h) => h.trim().toLowerCase());
        const criticalHeaders = ["timestamp", "type", "price"];
        // Optional headers: "label", "color", "icon"
        const missingCriticalHeaders = criticalHeaders.filter(
          (col) => !header.includes(col)
        );

        if (missingCriticalHeaders.length > 0) {
          this.message = `Signal CSV missing critical columns: ${missingCriticalHeaders.join(
            ", "
          )}. Required: ${criticalHeaders.join(", ")}`;
          this.messageType = "error";
          this.isValidFile = false;
          // No need to throw here if message is set, but ensure input is cleared in calling function if validation fails
        } else {
          // this.message = `File ${file.name} headers are valid.`; // This message is better set in handleFileChange
          // this.messageType = "info";
          this.isValidFile = true; // Headers are valid
        }
      } catch (e) {
        // Catch errors from readFileContent or other unexpected issues during validation
        this.message = "Error reading or validating signal file headers.";
        this.messageType = "error";
        this.isValidFile = false;
        console.error("Error during signal file header validation:", e);
        // Optionally re-throw or ensure calling function handles UI reset
      }
    },
    async handleUpload() {
      if (!this.selectedFile) {
        this.message = "Please select a file first.";
        this.messageType = "error";
        this.isValidFile = false; // Ensure this is also set
        return;
      }

      if (!this.isValidFile) {
        if (!this.message || this.messageType !== "error") {
          this.message =
            "The selected signal file is not valid. Please check headers.";
          this.messageType = "error";
        }
        // Clear input if validation failed and user clicks upload (though button should ideally prevent this)
        if (this.$refs.fileInputSignal) {
          this.$refs.fileInputSignal.value = null;
        }
        this.selectedFile = null;
        return;
      }

      this.isLoading = true;
      this.message = "Processing signal file...";
      this.messageType = "info";

      try {
        // parseSignalCsv will do the full parsing and data transformation
        const processedSignals = await this.parseSignalCsv(this.selectedFile);
        this.$emit("signal-data-uploaded", processedSignals);

        this.message = `Successfully processed ${processedSignals.length} signal(s) from ${this.selectedFile.name}.`;
        this.messageType = "success";
        if (this.$refs.fileInputSignal) {
          this.$refs.fileInputSignal.value = null; // Reset file input
        }
        this.selectedFile = null; // Clear selected file after successful upload
        this.isValidFile = false; // Reset validation status
      } catch (error) {
        this.message = `Error: ${
          error.message || "Could not process signal file."
        }`;
        this.messageType = "error";
        // If parsing fails (which includes its own header check now too, but this is more for content errors)
        // we might want to keep selectedFile so user doesn't have to re-select, but input should be clearable
        // For now, just show error. The initial client-side check is for quick feedback.
      } finally {
        this.isLoading = false;
      }
    },
    async parseSignalCsv(file) {
      let fileText;
      try {
        fileText = await this.readFileContent(file);
        // console.log("[SignalUpload] Raw fileText:", fileText); // LOG 1
      } catch (readError) {
        console.error("Failed to read the signal file for parsing.", readError);
        throw new Error("Failed to read the signal file for parsing.");
      }

      try {
        const initialSplit = fileText.split("\n");
        // console.log("[SignalUpload] After split('\n'):", JSON.parse(JSON.stringify(initialSplit))); // LOG 2 (updated)

        const trimmedLines = initialSplit.map((line) => line.trim());
        // console.log("[SignalUpload] After map(trim):", JSON.parse(JSON.stringify(trimmedLines))); // LOG 3

        const lines = trimmedLines.filter((line) => line);
        // console.log("[SignalUpload] After filter(line => line):", JSON.parse(JSON.stringify(lines))); // LOG 4
        // console.log("[SignalUpload] Final lines.length:", lines.length); // LOG 5

        if (lines.length === 0) {
          // Handle empty file
          throw new Error("Signal CSV file is empty.");
        }
        if (lines.length <= 1 && lines[0].trim() !== "") {
          // Handle header-only file
          this.message =
            "Signal CSV file only contains a header row or is empty.";
          this.messageType = "error";
          this.isValidFile = false; // Set this as it implies an invalid structure for signals
          throw new Error(
            "Signal CSV file only contains a header row or is empty."
          );
        } else if (lines.length <= 1 && lines[0].trim() === "") {
          // Re-check empty after split
          this.message = "Signal CSV file is effectively empty.";
          this.messageType = "error";
          this.isValidFile = false;
          throw new Error("Signal CSV file is effectively empty.");
        }

        const header = lines[0].split(",").map((h) => h.trim().toLowerCase());
        const expectedHeaders = [
          "timestamp",
          "type",
          "price",
          "label",
          "color",
          "icon",
        ];
        const headerMap = {};
        let allHeadersPresent = true;
        expectedHeaders.forEach((eh) => {
          const index = header.indexOf(eh);
          headerMap[eh] = index;
          // Critical headers check again, could be refactored but good for safety
          if (["timestamp", "type", "price"].includes(eh) && index === -1) {
            allHeadersPresent = false;
          }
        });

        if (!allHeadersPresent) {
          const missingCritical = ["timestamp", "type", "price"].filter(
            (ch) => headerMap[ch] === -1
          );
          throw new Error(
            `Signal CSV must contain at least timestamp, type, and price columns. Missing: ${missingCritical.join(
              ", "
            )}`
          );
        }

        const signals = [];
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(",");
          // Ensure values array is not too short for critical mapped headers
          if (
            values.length <=
            Math.max(
              headerMap["timestamp"],
              headerMap["type"],
              headerMap["price"]
            )
          ) {
            console.warn(
              `[SignalUpload] Skipping signal row due to insufficient columns: ${lines[i]}`
            );
            continue;
          }

          const timestampStr = values[headerMap["timestamp"]];
          const priceStr = values[headerMap["price"]];
          const timestamp = Number(timestampStr);
          const price = Number(priceStr);

          if (isNaN(timestamp) || isNaN(price)) {
            console.warn(
              `[SignalUpload] Skipping signal row due to invalid timestamp or price: ${lines[i]}`
            );
            continue;
          }

          let tradeTypeNumeric;
          const csvTypeUpper = (
            values[headerMap["type"]] || "INFO"
          ).toUpperCase();

          if (csvTypeUpper === "BUY") {
            tradeTypeNumeric = 1;
          } else {
            tradeTypeNumeric = 0;
          }
          const signalLabel =
            values[headerMap["label"]] !== undefined &&
            values[headerMap["label"]] !== ""
              ? values[headerMap["label"]]
              : csvTypeUpper;
          const signalColor =
            values[headerMap["color"]] ||
            (tradeTypeNumeric === 1 ? "green" : "red");

          const signalObject = {
            name: `${signalLabel} @ ${timestamp}`,
            type: "Trades",
            data: [[timestamp, tradeTypeNumeric, price, signalLabel]],
            settings: {
              showLabel: true,
              labelColor: signalColor,
            },
          };
          signals.push(signalObject);
        }
        return signals; // Async function implicitly returns Promise.resolve(signals)
      } catch (parseError) {
        console.error("Error parsing CSV content:", parseError);
        // Re-throw the error so it's caught by handleUpload's try-catch
        if (parseError instanceof Error) {
          throw new Error(
            `Failed to parse signal CSV file: ${parseError.message}`
          );
        }
        throw new Error(
          "Failed to parse signal CSV file. Check format and content."
        );
      }
    },
  },
};
</script>

<style scoped>
.signal-upload-container {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
  margin-bottom: 20px;
  text-align: left;
}

.signal-upload-container h4 {
  margin-top: 0;
  margin-bottom: 15px; /* Reduced from a likely default or larger value */
  color: #333;
  font-size: 1em;
}

.file-input-container {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* Basic styling for input and button, can be enhanced */
input[type="file"] {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.9em;
}

button {
  padding: 8px 15px;
  background-color: #007bff; /* Blue */
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  min-width: 100px;
  text-align: center;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

.upload-message {
  font-size: 0.9em;
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
  width: calc(100% - 16px); /* Take padding into account */
  box-sizing: border-box; /* Add box-sizing */
}

.upload-message.status-success {
  background-color: #e6ffed;
  border-left: 5px solid #4caf50; /* Green for success */
  color: #2e7d32;
}

.upload-message.status-error {
  background-color: #ffebee;
  border-left: 5px solid #f44336; /* Red for error */
  color: #c62828;
  font-weight: bold;
}

.upload-message.status-info {
  background-color: #e3f2fd;
  border-left: 5px solid #2196f3; /* Blue for info */
  color: #1565c0;
}
</style>
