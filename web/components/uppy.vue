<template>
  <div class="Uppy-container" ref="uppyContainer"></div>
</template>

<style lang="scss">
@import "@uppy/core/dist/style.min.css";
@import "@uppy/dashboard/dist/style.min.css";
@import "@uppy/webcam/dist/style.min.css";

.Uppy-container {
  z-index: 1;
  position: relative;

  .uppy-Dashboard-inner {
    border-radius: $border-radius-root;
  }
}
</style>

<script>
import Uppy from "@uppy/core";
import Dashboard from "@uppy/dashboard";
import Webcam from "@uppy/webcam";
import XHRUpload from "@uppy/xhr-upload";

export default {
  props: {
    config: Object
  },
  mounted() {
    this.uppy = Uppy(
      this.config || {
        restrictions: {
          allowedFileTypes: ["image/jpeg", "image/png"]
        }
      }
    )
      .use(Webcam, {
        modes: ["picture"],
        preferredImageMimeType: "image/jpeg",
        facingMode: "environment",
        mirror: false
      })
      .use(Dashboard, {
        target: this.$refs.uppyContainer,
        inline: true,
        hideUploadButton: true,
        theme: "light",
        width: "100%",
        plugins: ["Webcam"]
      })
      .use(XHRUpload, {
        timeout: 0,
        formData: true,
        fieldName: "file",
        endpoint: "https://dummy.restapiexample.com/api/v1/create"
      });

    this.uppy.on("file-added", file => this.$emit("file-added", file));
    this.uppy.on("file-removed", file => this.$emit("file-removed", file));
    this.uppy.on("complete", result => this.$emit("complete", result));
  },
  methods: {
    upload() {
      return this.uppy.upload();
    }
  },
  beforeDestroy() {
    this.uppy.close();
  }
};
</script>