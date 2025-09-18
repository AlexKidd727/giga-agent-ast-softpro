import React, { useEffect, useRef, useState } from "react";
import styled from "styled-components";
import { DemoItem } from "../interfaces.ts";
import { useFileUpload } from "../hooks/useFileUploads.ts";
import { Check, CopyX, Paperclip, Play, Save } from "lucide-react";
import {
  AttachmentBubble,
  AttachmentsContainer,
  CircularProgress,
  EnlargedImage,
  ImagePreview,
  ProgressOverlay,
  RemoveButton,
} from "./Attachments.tsx";
import OverlayPortal from "./OverlayPortal.tsx";
import { useNavigate } from "react-router-dom";
import { useDemoItems } from "../hooks/DemoItemsProvider.tsx";

interface DemoItemEditorProps {
  item: DemoItem;
  itemIdx: number;
}

const MAX_TEXTAREA_HEIGHT = 200;

const ItemEditor = styled.div`
  display: flex;
  flex-direction: row;
`;

const TextArea = styled.textarea`
  flex: 1;
  min-height: 60px;
  max-height: 200px;
  resize: none;
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu,
    Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
  padding: 12px;
  border: none;
  border-radius: 6px;
  background-color: #2d2d2d;
  color: #ffffff;
  font-size: 16px;
  line-height: 1.4;
  overflow-y: auto;
  outline: none;

  &::placeholder {
    color: #999999;
  }
`;

const NumberInput = styled.input`
  padding: 12px;
  border: none;
  border-radius: 6px;
  background-color: #2d2d2d;
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu,
    Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
  color: white;
`;

const FileInput = styled.input`
  display: none;
`;

const IconButton = styled.button`
  width: 40px;
  height: 40px;
  padding: 0;
  border: none;
  border-radius: 50%;
  color: #ffffff;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;

  &:hover {
    //background-color: #3b3b3b;
  }

  &:disabled {
    //background-color: #2d2d2d;
    cursor: not-allowed;
  }
`;

const ApproveButton = styled(IconButton)`
  background-color: #28a745;
  color: white;

  &:hover:not(:disabled) {
    background-color: #218838;
  }
`;

// Красная кнопка ✖️
const CancelButton = styled(IconButton)`
  background-color: #dc3545;
  color: white;

  &:hover:not(:disabled) {
    background-color: #c82333;
  }
`;

const SendButton = styled(IconButton)`
  //background-color: #005bb5;
  //color: white;
  //
  //&:hover:not(:disabled) {
  //  background-color: #0159b0;
  //}
`;

const EditorPart = styled.div`
  margin-right: 5px;
  display: flex;
  align-items: center;
`;

const CheckboxContainer = styled.label`
  display: flex;
  align-items: center;
  padding: 8px;
  position: relative;
  cursor: pointer;
  font-size: 14px;
  color: #fff;
`;

const HiddenCheckbox = styled.input.attrs({ type: "checkbox" })`
  border: 0;
  clip: rect(0 0 0 0);
  clippath: inset(50%);
  height: 1px;
  margin: -1px;
  overflow: hidden;
  padding: 0;
  position: absolute;
  white-space: nowrap;
  width: 1px;
`;

const StyledCheckbox = styled.div<{ checked: boolean }>`
  width: 16px;
  height: 16px;
  background: ${(p) => (p.checked ? "#4caf50" : "#555")};
  border-radius: 4px;
  transition: all 150ms;
  display: flex;
  align-items: center;
  justify-content: center;
  svg {
    visibility: ${(p) => (p.checked ? "visible" : "hidden")};
  }
`;

const DemoItemEditor: React.FC<DemoItemEditorProps> = ({ item, itemIdx }) => {
  const textRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [enlargedImage, setEnlargedImage] = useState<string | null>(null);
  const {
    uploadFiles,
    resetUploads,
    setExistingFiles,
    items,
    removeItem: removeAttachmentItem,
    getAllFileData,
  } = useFileUpload();
  const [steps, setSteps] = useState(10);
  const [active, setActive] = useState(false);
  const [message, setMessage] = useState("");
  const navigate = useNavigate();
  const { removeItem, updateItem } = useDemoItems();

  useEffect(() => {
    setMessage(item.json_data.message ? item.json_data.message : "");
    setExistingFiles(item.json_data.attachments ? item.json_data.attachments : []);
    setSteps(item.steps);
    setActive(item.active);
  }, [item.json_data, item.steps, item.active, setExistingFiles]);

  // при первом рендере и при очистке
  useEffect(() => {
    autoResize();
  }, [message]);

  // автоподгон высоты
  const autoResize = () => {
    const el = textRef.current;
    if (!el) return;
    el.style.height = "auto";
    const newHeight = Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT);
    el.style.height = `${newHeight}px`;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      uploadFiles(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const handleDelete = () => {
    // eslint-disable-next-line no-restricted-globals
    if (confirm("Подтверждаете удаление?")) {
      removeItem(item.id);
    }
  };

  const openLink = (url: string) => {
    // @ts-ignore
    window.open(url, "_blank").focus();
  };

  const handlePlay = () => {
    navigate(`/demo/${itemIdx}`);
  };

  const handleSave = () => {
    const allFiles = getAllFileData();
    const data: DemoItem = {
      id: item.id,
      json_data: {
        message: message,
        attachments: allFiles,
      },
      steps: steps,
      sorting: item.sorting,
      active: active,
    };
    updateItem(data);
  };

  return (
    <div style={{ padding: "20px" }}>
      <ItemEditor>
        <EditorPart>
          <CheckboxContainer>
            <HiddenCheckbox
              checked={active}
              onChange={() => setActive(!active)}
            />
            <StyledCheckbox checked={active}>
              <Check size={12} />
            </StyledCheckbox>
          </CheckboxContainer>
        </EditorPart>
        <EditorPart style={{ flex: 3, flexDirection: "row" }}>
          <IconButton
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Добавить вложения"
          >
            <Paperclip />
          </IconButton>
          <TextArea
            placeholder="Спросите что-нибудь…"
            ref={textRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <FileInput
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
          />
        </EditorPart>
        <EditorPart>
          <NumberInput
            value={steps}
            type={"number"}
            onChange={(e) => setSteps(e.target.valueAsNumber)}
          />
        </EditorPart>
        <EditorPart style={{ flexDirection: "column" }}>
          <CancelButton
            title="Удалить"
            onClick={handleDelete}
            style={{ marginBottom: "5px" }}
          >
            <CopyX />
          </CancelButton>
          <ApproveButton title="Сохранить" onClick={handleSave}>
            <Save />
          </ApproveButton>
        </EditorPart>
        <EditorPart>
          <SendButton title="Запустить" onClick={handlePlay}>
            <Play />
          </SendButton>
        </EditorPart>
        <OverlayPortal
          isVisible={!!enlargedImage}
          onClose={() => setEnlargedImage(null)}
        >
          <EnlargedImage src={enlargedImage ?? ""} />
        </OverlayPortal>
      </ItemEditor>
      <EditorPart style={{ flexDirection: "row", width: "100%" }}>
        {items.length > 0 && (
          <AttachmentsContainer>
            {items.map((it, idx) => (
              <AttachmentBubble
                key={idx}
                onClick={() => {
                  if (it.kind === "existing") {
                    const f = it.data!;
                    if (f.file_id) setEnlargedImage("/files/" + f.path);
                    else openLink("/files/" + f.path);
                  } else if (it.previewUrl) {
                    setEnlargedImage(it.previewUrl);
                  }
                }}
              >
                {it.kind === "existing" ? (
                  it.data?.file_id ? (
                    <ImagePreview src={"/files/" + it.data.path} />
                  ) : (
                    <span>{it.name ?? it.data?.path.replace(/^files\//, "")}</span>
                  )
                ) : it.previewUrl ? (
                  <ImagePreview src={it.previewUrl} />
                ) : (
                  <span>{it.name}</span>
                )}

                {it.progress < 100 && (
                  <ProgressOverlay>
                    <CircularProgress progress={it.progress}>
                      {it.progress}%
                    </CircularProgress>
                  </ProgressOverlay>
                )}

                <RemoveButton
                  onClick={(e) => {
                    e.stopPropagation();
                    removeAttachmentItem(idx);
                  }}
                >
                  ×
                </RemoveButton>
              </AttachmentBubble>
            ))}
          </AttachmentsContainer>
        )}
      </EditorPart>
    </div>
  );
};

export default React.memo(
  DemoItemEditor,
  (prev, next) => prev.item === next.item && prev.itemIdx === next.itemIdx,
);
