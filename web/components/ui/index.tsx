import * as React from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  Controller,
  ControllerProps,
  FieldPath,
  FieldValues,
  FormProvider,
  useFormContext,
} from "react-hook-form";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- BUTTON ---

export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { 
    variant?: "default" | "outline" | "ghost" | "destructive" | "link";
    size?: "default" | "sm" | "lg" | "icon";
  }
>
(({ className, variant = "default", size = "default", ...props }, ref) => {
  const variants = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm shadow-primary/20",
    outline: "border border-neutral-200 dark:border-neutral-800 bg-background hover:bg-neutral-50 dark:hover:bg-neutral-900 text-neutral-600 dark:text-neutral-400",
    ghost: "hover:bg-neutral-100 dark:hover:bg-neutral-800",
    link: "text-primary underline-offset-4 hover:underline",
    destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-sm shadow-destructive/20",
  };

  const sizes = {
    default: "h-9 px-4",
    sm: "h-8 rounded-md px-3 text-xs",
    lg: "h-10 rounded-lg px-6 text-base",
    icon: "h-8 w-8",
  };

  return (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-lg text-xs font-bold transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 active:scale-95",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
});
Button.displayName = "Button";

// --- PROGRESS ---

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800", className)}>
      <div
        className="h-full bg-primary transition-all duration-500 ease-out"
        style={{ width: `${value || 0}%` }}
      />
    </div>
  );
}

// --- INPUT ---

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900 px-3 py-1.5 text-xs transition-all file:border-0 file:bg-transparent file:text-xs file:font-medium placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

// --- FORM PRIMITIVES ---

export const Form = FormProvider;

interface FormFieldContextValue<
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
> {
  name: TName;
}

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue
);

export const FormField = <
  TFieldValues extends FieldValues = FieldValues,
  TName extends FieldPath<TFieldValues> = FieldPath<TFieldValues>
>({
  ...props
}: ControllerProps<TFieldValues, TName>) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  );
};

export const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext);
  const itemContext = React.useContext(FormItemContext);
  const { getFieldState, formState } = useFormContext();

  const fieldState = getFieldState(fieldContext.name, formState);

  if (!fieldContext) {
    throw new Error("useFormField should be used within <FormField>");
  }

  const { id } = itemContext;

  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  };
};

interface FormItemContextValue {
  id: string;
}

const FormItemContext = React.createContext<FormItemContextValue>(
  {} as FormItemContextValue
);

export const FormItem = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => {
  const id = React.useId();

  return (
    <FormItemContext.Provider value={{ id }}>
      <div ref={ref} className={cn("space-y-1.5", className)} {...props} />
    </FormItemContext.Provider>
  );
});
FormItem.displayName = "FormItem";

export const FormLabel = React.forwardRef<
  HTMLLabelElement,
  React.LabelHTMLAttributes<HTMLLabelElement>
>(({ className, ...props }, ref) => {
  const { error, formItemId } = useFormField();

  return (
    <label
      ref={ref}
      className={cn(
        "text-xs font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        error && "text-destructive",
        className
      )}
      htmlFor={formItemId}
      {...props}
    />
  );
});
FormLabel.displayName = "FormLabel";

export const FormControl = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ ...props }, ref) => {
  const { error, formItemId, formDescriptionId, formMessageId } = useFormField();

  return (
    <div
      ref={ref}
      id={formItemId}
      aria-describedby={
        !error
          ? `${formDescriptionId}`
          : `${formDescriptionId} ${formMessageId}`
      }
      aria-invalid={!!error}
      {...props}
    />
  );
});
FormControl.displayName = "FormControl";

export const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  const { error, formMessageId } = useFormField();
  const body = error ? String(error?.message) : children;

  if (!body) {
    return null;
  }

  return (
    <p
      ref={ref}
      id={formMessageId}
      className={cn("text-xs font-bold text-destructive", className)}
      {...props}
    >
      {body}
    </p>
  );
});
FormMessage.displayName = "FormMessage";
