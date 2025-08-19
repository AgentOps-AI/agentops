import { CheckCircledIcon, CrossCircledIcon, QuestionMarkCircledIcon } from '@radix-ui/react-icons';

export const end_states = [
  {
    value: 'Indeterminate',
    label: 'Indeterminate',
    icon: QuestionMarkCircledIcon,
  },
  {
    value: 'Success',
    label: 'Success',
    icon: CheckCircledIcon,
  },
  {
    value: 'Fail',
    label: 'Fail',
    icon: CrossCircledIcon,
  },
];
