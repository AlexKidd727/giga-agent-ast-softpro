import { Message } from "@langchain/langgraph-sdk";

export interface GraphState extends Record<string, unknown> {
  messages: Message[];
}

export interface FileData {
  path: string;
  file_id?: string;
}

export interface MessageData {
  message: string;
  attachments: FileData[];
}

export interface DemoItem {
  id: string;
  json_data: Partial<MessageData>;
  steps: number;
  sorting: number;
  active: boolean;
}
