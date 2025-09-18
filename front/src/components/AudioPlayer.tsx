import React, { useEffect, useState } from "react";
import styled from "styled-components";
import { StoreClient } from "@langchain/langgraph-sdk/client";

const Placeholder = styled.div`
  width: 100%;
  height: 100px;
  background-color: #2d2d2d;
  position: relative;
`;

interface HTMLPageProps {
  id: string;
  alt?: string;
}

const AudioPlayer: React.FC<HTMLPageProps> = ({ id, alt }) => {
  const [attachment, setAttachment] = useState<any | null>(null);
  const [error, setError] = useState<boolean>(false);
  const client = new StoreClient({
    apiUrl: `${window.location.protocol}//${window.location.host}/graph`,
  });

  useEffect(() => {
    client
      .getItem(["audio"], id)
      .then((res) => {
        setAttachment(res?.value);
      })
      .catch(() => {
        setError(true);
      });
  }, [id]);

  if (error) {
    return <div>Ошибка загрузки вложения {alt || ""}</div>;
  }
  if (!attachment) {
    return <Placeholder />; // можно заменить на спиннер или skeleton
  }
  return (
    <audio
      controls={true}
      style={{ marginTop: "5px", marginBottom: "5px", display: "block" }}
    >
      <source src={`data:audio/mp3;base64, ${attachment.data}`} />
    </audio>
  );
};

export default React.memo(
  AudioPlayer,
  (prev, next) => prev.id === next.id && prev.alt === next.alt,
);
