import React, { useEffect, useMemo, useState } from "react";
import styled from "styled-components";
import { StoreClient } from "@langchain/langgraph-sdk/client";
import { useSelectedAttachments } from "../hooks/SelectedAttachmentsContext.tsx";
import { Check } from "lucide-react";
// @ts-ignore
import Plot from "react-plotly.js";

const Placeholder = styled.div`
  width: 100%;
  padding-top: 56.25%; /* подложка под изображение, чтобы не прыгал layout */
  background-color: #2d2d2d;
  position: relative;
`;

const Img = styled.img`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
`;

const PlotWrapper = styled.div`
  .modebar-container,
  .modebar .modebar-group {
    background: rgba(0, 0, 0, 0) !important;
  }
`;

const SelectableContainer = styled.div`
  position: relative;
`;

const SelectorButton = styled.button<{ $selected: boolean, isGraph: boolean }>`
  position: absolute;
  top: ${({isGraph}) => (isGraph ? "40px" : "8px")};
  right: 8px;
  width: 24px;
  height: 24px;
  z-index: 1000;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background-color: ${({ $selected }) => ($selected ? "#1976d2" : "transparent")};
  border: ${({ $selected }) => ($selected ? "1px solid #1976d2" : "1px solid #fff")};
  color: #fff;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.2);
    @media print {
    display: none;
  }

  &:hover {
    transform: scale(1.05);
  }
`;

interface GraphImageProps {
  id: string;
  alt?: string;
}

const GraphImage: React.FC<GraphImageProps> = ({ id, alt }) => {
  const [attachment, setAttachment] = useState<any | null>(null);
  const [error, setError] = useState<boolean>(false);
  const client = new StoreClient({
    apiUrl: `${window.location.protocol}//${window.location.host}/graph`,
  });
  const { isSelected, toggle } = useSelectedAttachments();
  const selected = isSelected(id);

  useEffect(() => {
    client
      .getItem(["attachments"], id)
      .then((res) => {
        setAttachment(res?.value);
      })
      .catch(() => {
        setError(true);
      });
  }, [id]);

  if (error) {
    return <div>Ошибка загрузки изображения {alt || ""}</div>;
  }
  if (!attachment) {
    return <Placeholder />; // можно заменить на спиннер или skeleton
  }
  if (attachment["type"] === "application/vnd.plotly.v1+json") {
    const fig = attachment["data"];
    const layout = {
      ...fig.layout,
      template: "plotly_dark",
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#fff" },
      xaxis: {
        ...fig.layout?.xaxis,
        gridcolor: "rgba(255,255,255,0.2)",
        zerolinecolor: "rgba(255,255,255,0.2)",
      },
      yaxis: {
        ...fig.layout?.yaxis,
        gridcolor: "rgba(255,255,255,0.2)",
        zerolinecolor: "rgba(255,255,255,0.2)",
      },
    };
    return (
      <SelectableContainer>
        <SelectorButton
          aria-label="select-attachment"
          isGraph={true}
          $selected={selected}
          onClick={(e) => {
            e.stopPropagation();
            toggle(id, alt);
          }}
        >
          {selected ? <Check size={24} /> : null}
        </SelectorButton>
        <PlotWrapper>
          <Plot
            data={fig.data}
            layout={layout}
            useResizeHandler
            style={{ width: "100%" }}
          />
        </PlotWrapper>
      </SelectableContainer>
    );
  }
  if (attachment["type"] === "image/png") {
    return (
      <SelectableContainer>
        <SelectorButton
          aria-label="select-attachment"
          isGraph={false}
          $selected={selected}
          onClick={(e) => {
            e.stopPropagation();
            toggle(id, alt);
          }}
        >
          {selected ? <Check size={24} /> : null}
        </SelectorButton>
        <div style={{ display: "flex" }}>
          <img
            src={`data:image/png;base64,${attachment["data"]}`}
            alt={`attachment-${attachment["file_id"]}`}
            style={{
              maxWidth: "100%",
              borderRadius: "4px",
              margin: "auto",
            }}
          />
        </div>
      </SelectableContainer>
    );
  }
};

export default React.memo(
  GraphImage,
  (prev, next) => prev.id === next.id && prev.alt === next.alt,
);
