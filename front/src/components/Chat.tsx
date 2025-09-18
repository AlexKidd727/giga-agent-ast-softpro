import React, { useMemo } from "react";
import styled from "styled-components";
import MessageList from "./MessageList";
import InputArea from "./InputArea";
import { useStream } from "@langchain/langgraph-sdk/react";
import { PROGRESS_AGENTS } from "../config.ts";
import { useStableMessages } from "../hooks/useStableMessages";
import { GraphState } from "../interfaces";
import { useNavigate, useParams } from "react-router-dom";
import { uiMessageReducer } from "@langchain/langgraph-sdk/react-ui";
import { SelectedAttachmentsProvider } from "../hooks/SelectedAttachmentsContext.tsx";

const ChatWrapper = styled.div`
  width: 100%;
  display: flex;
  padding: 20px;
  @media (max-width: 900px) {
    padding: 0;
    margin-top: 75px;
  }
`;

const ChatContainer = styled.div`
  display: flex;
  max-width: 900px;
  margin: auto;
  height: 100%;
  flex-direction: column;
  flex: 1;
  background-color: #212121d9;
  backdrop-filter: blur(20px);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 0 50px #00000075;
  @media print {
    overflow: visible;
    box-shadow: none;
    background-color: #1f1f1f;
  }
  @media (max-width: 900px) {
    background-color: #1f1f1f;
    box-shadow: none;
  }
`;

const Chat: React.FC = () => {
  const navigate = useNavigate();
  const { threadId } = useParams<{ threadId?: string }>();
  const thread = useStream<GraphState>({
    apiUrl: `${window.location.protocol}//${window.location.host}/graph`,
    assistantId: "chat",
    messagesKey: "messages",
    threadId: threadId === undefined ? null : threadId,
    onThreadId: (threadId: string) => {
      navigate(`/threads/${threadId}`);
    },
    onCustomEvent: (event, options) => {
      options.mutate((prev) => {
        // @ts-ignore
        const ui = uiMessageReducer(prev.ui ?? [], event);
        return { ...prev, ui };
      });
    },
  });
  const agentProgress = useMemo(() => {
    // @ts-ignore
    const uis = (thread.values.ui ?? []).filter(
      // @ts-ignore
      (el) => el.name === "agent_execution",
    );
    if (uis.length) {
      // @ts-ignore
      const agent = PROGRESS_AGENTS[uis.at(-1).props.agent];
      if (agent) {
        return agent[uis.at(-1).props.node];
      }
      return null;
    }
    return null;
  }, [thread.values.ui]);

  const stableMessages = useStableMessages(thread);

  return (
    <SelectedAttachmentsProvider>
      <ChatWrapper>
        <ChatContainer>
          <MessageList
            messages={stableMessages ?? []}
            thread={thread}
            progressAgent={agentProgress}
          />
          <InputArea thread={thread} />
        </ChatContainer>
      </ChatWrapper>
    </SelectedAttachmentsProvider>
  );
};

export default Chat;
