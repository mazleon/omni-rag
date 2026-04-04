'use client';

import { useRef, useState } from 'react';
import { Upload, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';

interface UploadDropzoneProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
  collectionId?: string;
}

const ACCEPTED = '.pdf,.doc,.docx,.txt,.md,.xlsx,.csv,.pptx,.png,.jpg,.jpeg';

export function UploadDropzone({ onUpload, isUploading }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    onUpload(files[0]);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      className={cn(
        'flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-8 transition-colors',
        isDragging
          ? 'border-blue-500 bg-blue-500/5'
          : 'border-slate-700 bg-slate-800/30 hover:border-slate-600',
      )}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-800">
        {isUploading ? (
          <FileText className="h-6 w-6 animate-pulse text-blue-400" />
        ) : (
          <Upload className="h-6 w-6 text-slate-400" />
        )}
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-slate-300">
          {isUploading ? 'Uploading…' : 'Drop a file here'}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">PDF, DOCX, XLSX, PPTX, TXT, images</p>
      </div>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => inputRef.current?.click()}
        disabled={isUploading}
      >
        Choose file
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
