import { useRef } from "react";
import { UploadCard } from "@/components/app/UploadCard";
import { Button } from "@/components/shared/Button";
import { EmptyState } from "@/components/shared/EmptyState";
import { ErrorState } from "@/components/shared/ErrorState";
import { PageContainer } from "@/components/shared/PageContainer";
import { Spinner } from "@/components/shared/Spinner";
import { UPLOAD_ACCEPT } from "@/lib/uploads";
import type { UploadedAsset } from "@/types/upload";

interface UploadsPanelProps {
  uploads: UploadedAsset[];
  error: string | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
}

export function UploadsPanel({ uploads, error, isUploading, onUpload }: UploadsPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  return (
    <PageContainer className="min-w-0 space-y-6 px-4 py-6 sm:px-6">
      <input
        ref={fileInputRef}
        data-testid="uploads-panel-file-input"
        type="file"
        className="hidden"
        accept={UPLOAD_ACCEPT}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            onUpload(file);
            event.currentTarget.value = "";
          }
        }}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">Upload datasets</p>
          <p className="mt-1 text-sm text-muted">Add a CSV or JSON file to profile it and make it available for analysis.</p>
        </div>
        <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
          {isUploading ? <Spinner className="h-4 w-4" /> : null}
          Upload file
        </Button>
      </div>

      {error ? <ErrorState title="Upload issue" description={error} /> : null}

      {uploads.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {uploads.map((asset) => (
            <UploadCard key={asset.id} asset={asset} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No uploads yet"
          description="Upload a CSV or JSON file to profile it here before you ask the next question."
        />
      )}
    </PageContainer>
  );
}
