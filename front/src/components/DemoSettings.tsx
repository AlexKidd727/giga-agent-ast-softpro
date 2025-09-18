import React, { useEffect, useRef } from "react";
import styled from "styled-components";
import DemoItemEditor from "./DemoItemEditor.tsx";
import { useDemoItems } from "../hooks/DemoItemsProvider.tsx";
import { Plus } from "lucide-react";

const DemoWrapper = styled.div`
  width: 100%;
  display: flex;
  padding: 20px;
  @media (max-width: 900px) {
    padding: 0;
    margin-top: 75px;
  }
`;

const DemoContainer = styled.div`
  display: flex;
  max-width: 900px;
  margin: auto;
  height: 100%;
  flex: 1;
  background-color: #212121d9;
  backdrop-filter: blur(20px);
  border-radius: 8px;
  box-shadow: 0 0 50px #00000075;
  overflow: hidden;
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

const DemoItems = styled.div`
  overflow: auto;
  flex-direction: column;
  display: flex;
  width: 100%;
  height: 100%;
`;

const ButtonWrapper = styled.div`
  position: fixed;
  bottom: 10px;
  right: 10px;
`;

const IconButton = styled.button`
  width: 55px;
  height: 55px;
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

const AddButton = styled(IconButton)`
  background-color: #28a745;
  color: white;

  &:hover:not(:disabled) {
    background-color: #218838;
  }
`;

const Delimiter = styled.hr`
  width: 100%;
  border-color: #000000;
`;

interface DemoSettingsProps {}

const DemoSettings: React.FC<DemoSettingsProps> = () => {
  const { demoItems: items, addItem } = useDemoItems();
  const itemsRef = useRef<HTMLDivElement>(null);
  // храним предыдущую длину массива
  const prevLength = useRef(items.length);

  useEffect(() => {
    const el = itemsRef.current;
    // если новых элементов стало больше, чем было
    if (items.length > prevLength.current && el) {
      el.scrollTo({ top: el.scrollHeight + 100, behavior: "smooth" });
    }
    // обновляем сохранённую длину на текущее значение
    prevLength.current = items.length;
  }, [items.length]);
  const handleAdd = () => {
    addItem();
  };
  return (
    <DemoWrapper>
      <DemoContainer>
        <DemoItems ref={itemsRef}>
          {items
            .sort((a, b) => a.sorting - b.sorting)
            .map((item, idx) => (
              <div key={item.id}>
                <DemoItemEditor item={item} itemIdx={idx} />
                <Delimiter />
              </div>
            ))}
        </DemoItems>
        <ButtonWrapper>
          <AddButton onClick={handleAdd}>
            <Plus />
          </AddButton>
        </ButtonWrapper>
      </DemoContainer>
    </DemoWrapper>
  );
};

export default DemoSettings;
