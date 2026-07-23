import React, { useState } from "react";
import { useTranslation } from "react-i18next";

export default function DragDropUpload({ onFileSelect, acceptedTypes = ".pdf,.docx,.png,.jpg", maxSizeMB = 10 }) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);

  const validateFile = (file) => {
    if (!file) return false;

    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`Velikost souboru přesahuje povolený limit ${maxSizeMB} MB.`);
      return false;
    }

    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!acceptedTypes.includes(ext)) {
      setError(`Nepovolený typ souboru. Povoleny jsou ${acceptedTypes}.`);
      return false;
    }

    setError(null);
    return true;
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
        if (onFileSelect) onFileSelect(file);
      }
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
        if (onFileSelect) onFileSelect(file);
      }
    }
  };

  return (
    <div className="w-full my-4">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400 bg-gray-50"
        }`}
      >
        <input
          type="file"
          id="drag-drop-input"
          className="hidden"
          accept={acceptedTypes}
          onChange={handleFileInput}
        />
        <label htmlFor="drag-drop-input" className="cursor-pointer block">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
            aria-hidden="true"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20L28 8z"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M28 8v12h12"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="mt-2 text-sm text-gray-600">
            <span className="font-semibold text-blue-600">Klikněte pro výběr souboru</span> nebo přetáhněte sem
          </p>
          <p className="text-xs text-gray-500 mt-1">PDF, DOCX, PNG nebo JPG (max {maxSizeMB} MB)</p>
        </label>
      </div>

      {selectedFile && (
        <div className="mt-2 text-xs text-green-600 font-medium">
          Vybraný soubor: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
        </div>
      )}

      {error && <div className="mt-2 text-xs text-red-600 font-medium">{error}</div>}
    </div>
  );
}
