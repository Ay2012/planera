export type InspectionTabId = "sql" | "results" | "trace" | "validation";
export type InspectionStatus = "valid" | "warning" | "error" | "running";

export interface ResultTableData {
  columns: string[];
  rows: Array<Record<string, string | number | null>>;
}

export interface TraceEntry {
  id: string;
  label: string;
  description: string;
  detail: string;
  durationLabel: string;
  status: InspectionStatus | "complete";
}

export interface ValidationCheck {
  id: string;
  label: string;
  detail: string;
  status: "pass" | "warn" | "fail";
}

export interface MetadataItem {
  label: string;
  value: string;
}

export interface InspectionData {
  id: string;
  title: string;
  query: string;
  status: InspectionStatus;
  rowsReturned: number;
  runtimeMs: number | null;
  filters: string[];
  confidence: number;
  verified: boolean;
  dataSource: string;
  lastUpdated: string;
  engine: string;
  queryType: string;
  results: ResultTableData;
  trace: TraceEntry[];
  validation: ValidationCheck[];
  metadata: MetadataItem[];
}
