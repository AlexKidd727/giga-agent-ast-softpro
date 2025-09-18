import React, { useState } from "react";
import { Message } from "@langchain/langgraph-sdk";
import {
  AttachmentBubble,
  AttachmentsContainer,
  CloseButton,
  EnlargedImage,
  ImagePreview,
  Overlay,
} from "./Attachments.tsx";
import { FileData } from "../interfaces.ts";
import OverlayPortal from "./OverlayPortal.tsx";

interface MessageProps {
  message: Message;
}

const MessageAttachments: React.FC<MessageProps> = ({ message }) => {
  // @ts-ignore
  const uploads = (message.additional_kwargs?.files ?? []) as FileData[];
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null);

  const openLink = (url: string) => {
    // @ts-ignore
    window.open(url, "_blank").focus();
  };

  return (
    <>
      {uploads.length > 0 && (
        <AttachmentsContainer
          style={{ justifyContent: "flex-end", marginTop: "0" }}
        >
          {uploads.map((u: FileData, idx) => (
            <AttachmentBubble
              key={idx}
              onClick={() =>
                u.file_id
                  ? setEnlargedImage("/files/" + u.path)
                  : openLink("/files/" + u.path)
              }
            >
              {u.file_id ? (
                <ImagePreview src={"/files/" + u.path} />
              ) : (
                <span>{u.path.replace("files/", "")}</span>
              )}
            </AttachmentBubble>
          ))}
        </AttachmentsContainer>
      )}

      {enlargedImage && (
        <OverlayPortal
          isVisible={!!enlargedImage}
          onClose={() => setEnlargedImage(null)}
        >
          <EnlargedImage src={enlargedImage ?? ""} />
        </OverlayPortal>
      )}
    </>
  );
};

export default MessageAttachments;
