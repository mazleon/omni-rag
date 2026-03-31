"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { UploadCloud, File, AlertCircle } from "lucide-react";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "text/html": [".html"],
  "text/markdown": [".md"],
};

export function DocumentUploader({ onUpload }: { onUpload: (file: File) => Promise<void> }) {
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(
    async (files: File[]) => {
      setUploading(true);
      for (const file of files) {
        await onUpload(file);
      }
      setUploading(false);
    },
    [onUpload]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: 100 * 1024 * 1024, // 100MB
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-3xl p-16 text-center cursor-pointer transition-all duration-300 ease-in-out group ${
        isDragActive && !isDragReject
          ? "border-brand bg-brand/5 shadow-brand/10 shadow-inner scale-[1.02]"
          : isDragReject
          ? "border-destructive bg-destructive/10 cursor-not-allowed"
          : "border-muted-foreground/20 hover:border-brand/50 hover:bg-brand/5 hover:shadow-sm"
      }`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className={`p-4 rounded-full transition-colors duration-300 ${
            isDragActive && !isDragReject ? 'bg-brand/20 text-brand' : 'bg-muted text-muted-foreground group-hover:bg-brand/10 group-hover:text-brand'
        }`}>
            {isDragReject ? <AlertCircle className="size-8 text-destructive" /> : uploading ? <UploadCloud className="size-8 animate-bounce" /> : <UploadCloud className="size-8" />}
        </div>
        
        {uploading ? (
          <div className="space-y-1">
            <h3 className="font-semibold text-lg">Encrypting and uploading...</h3>
            <p className="text-sm text-muted-foreground">Please keep this window open.</p>
          </div>
        ) : (
          <div className="space-y-2">
            <h3 className="font-semibold text-xl tracking-tight text-foreground">
              {isDragActive ? "Drop documents here to ingest" : "Upload Enterprise Knowledge"}
            </h3>
            <p className="text-sm text-muted-foreground max-w-xs mx-auto">
              Drag & drop PDFs, Office files, Images, or Markdown. Maximum file size 100MB.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
