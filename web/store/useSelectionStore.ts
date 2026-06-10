import { create } from "zustand";

interface SelectionState {
  selectedIds: string[];
  isSelectionMode: boolean;
  
  // Actions
  toggleSelection: (id: string) => void;
  setSelectedIds: (ids: string[]) => void;
  clearSelection: () => void;
  setSelectionMode: (enabled: boolean) => void;
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedIds: [],
  isSelectionMode: false,

  toggleSelection: (id) => set((state) => {
    const isSelected = state.selectedIds.includes(id);
    const newSelection = isSelected 
      ? state.selectedIds.filter(i => i !== id)
      : [...state.selectedIds, id];
    
    return {
      selectedIds: newSelection,
      isSelectionMode: newSelection.length > 0
    };
  }),

  setSelectedIds: (ids) => set({ 
    selectedIds: ids,
    isSelectionMode: ids.length > 0
  }),

  clearSelection: () => set({ 
    selectedIds: [], 
    isSelectionMode: false 
  }),

  setSelectionMode: (enabled) => set((state) => ({ 
    isSelectionMode: enabled,
    selectedIds: enabled ? state.selectedIds : []
  })),
}));
