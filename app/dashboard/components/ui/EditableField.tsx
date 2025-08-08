import React from 'react';
import { Pencil2Icon, CheckIcon, Cross2Icon } from '@radix-ui/react-icons';

export interface EditableFieldProps {
  label: string;
  value: string;
  placeholder: string;
  fieldKey: string;
  isEditing: boolean;
  onEdit: () => void;
  onSave: (value: string) => void;
  onCancel: () => void;
  onChange: (value: string) => void;
}

const EditableField: React.FC<EditableFieldProps> = ({
  label,
  value,
  placeholder,
  fieldKey,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onChange,
}) => {
  const [localValue, setLocalValue] = React.useState(value);

  React.useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const handleSave = () => {
    onSave(localValue);
  };

  const handleCancel = () => {
    setLocalValue(value);
    onCancel();
  };

  return (
    <label className="text-[14px] text-[rgba(20,27,52,0.74)] mb-1 font-medium">
      {label}
      <div className="flex items-center gap-2 mt-1">
        <input
          type="text"
          placeholder={placeholder}
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          readOnly={!isEditing}
          className={`flex-1 p-2 text-[14px] border rounded text-[rgba(20,27,52,1)] placeholder-[rgba(20,27,52,0.68)] transition-all ${
            isEditing
              ? 'bg-white border-blue-400 ring-2 ring-blue-400 ring-opacity-50 shadow-lg focus:outline-none'
              : 'bg-[rgba(248,249,250,1)] border-[rgba(222,224,244,1)] focus:outline-none focus:ring-2 focus:ring-[rgba(20,27,52,0.68)] focus:border-[rgba(20,27,52,0.68)]'
          } ${!isEditing ? 'cursor-default' : ''}`}
        />
        <div className="flex items-center gap-1">
          {!isEditing ? (
            <button
              onClick={onEdit}
              className="w-8 h-8 flex items-center justify-center text-[rgba(20,27,52,0.5)] hover:text-[rgba(20,27,52,1)] hover:bg-[rgba(222,224,244,0.5)] rounded transition-colors"
              title="Edit"
            >
              <Pencil2Icon width={14} height={14} />
            </button>
          ) : (
            <>
              <button
                onClick={handleSave}
                className="w-8 h-8 flex items-center justify-center text-green-600 hover:text-green-700 hover:bg-green-50 rounded transition-colors"
                title="Save"
              >
                <CheckIcon width={14} height={14} />
              </button>
              <button
                onClick={handleCancel}
                className="w-8 h-8 flex items-center justify-center text-[rgba(230,90,126,1)] hover:text-[rgba(200,60,96,1)] hover:bg-[rgba(230,90,126,0.1)] rounded transition-colors"
                title="Cancel"
              >
                <Cross2Icon width={14} height={14} />
              </button>
            </>
          )}
        </div>
      </div>
    </label>
  );
};

export default EditableField; 