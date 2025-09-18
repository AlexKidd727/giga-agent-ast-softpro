import React, { useState, useRef, useEffect } from "react";
import styled from "styled-components";
import {
  EllipsisVertical,
  Printer,
  Settings as SettingsIcon,
  Check,
} from "lucide-react";
import { useSettings } from "./Settings.tsx";

const ToolBar: React.FC = () => {
  const { settings, setSettings } = useSettings();

  const handlePrint = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.print();
  };

  const handleSettings = (e: React.MouseEvent) => {
    e.stopPropagation();
  };

  const handleAutoApproveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings({ ...settings, ...{ autoApprove: e.target.checked } });
  };

  return <></>;
};

export default ToolBar;
