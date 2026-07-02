export type Role =
  "Administrator" | "Plant Manager" | "Maintenance Engineer" | "Safety Officer" | "Operator";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar?: string;
  department?: string;
}

export type DocStatus = "Uploading" | "Processing" | "Indexed" | "Failed";

export interface DocumentItem {
  id: string;
  name: string;
  department: string;
  type: "PDF" | "DOCX" | "XLSX" | "CSV" | "TXT" | "Image";
  status: DocStatus;
  uploadedBy: string;
  date: string;
  size: string;
  tags: string[];
  machine?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: { doc: string; page?: number }[];
  createdAt: string;
  conversationId?: string;
}

export interface Conversation {
  id: string;
  title: string;
  pinned?: boolean;
  folder?: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface DashboardStats {
  totalDocuments: number;
  departments: number;
  graphNodes: number;
  queriesToday: number;
  pendingCompliance: number;
  openMaintenance: number;
  avgResponseMs: number;
}

export interface ComplianceItem {
  id: string;
  name: string;
  regulation: string;
  status: "Passed" | "Pending" | "Critical" | "Expired";
  lastAudit: string;
  owner: string;
}

export interface MaintenanceTask {
  id: string;
  equipment: string;
  type: "Preventive" | "Corrective" | "Inspection";
  due: string;
  status: "Open" | "In Progress" | "Done" | "Overdue";
  assignee: string;
  priority: "Low" | "Medium" | "High" | "Critical";
}

export interface GraphNode {
  id: string;
  label: string;
  type: "Machine" | "Department" | "Procedure" | "Person" | "Regulation" | "Failure" | "Task";
  x: number;
  y: number;
}
export interface GraphEdge {
  from: string;
  to: string;
  label: string;
}
