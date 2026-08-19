import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"

export type CalendarProps = React.ComponentProps<typeof DayPicker> & {
  theme?: 'light' | 'dark';
}

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  theme,
  ...props
}: CalendarProps) {
  const isLight = theme === 'light';
  
  return (
    <>
      {isLight && (
        <style>{`
          /* Light mode calendar styling - ULTRA AGGRESSIVE targeting to ensure dates are visible */
          .calendar-light-mode button,
          .calendar-light-mode button *,
          .calendar-light-mode .rdp button,
          .calendar-light-mode .rdp button * {
            color: #1e293b !important;
          }
          
          /* Target ALL day buttons regardless of class names */
          .calendar-light-mode button[role="gridcell"] button,
          .calendar-light-mode table button,
          .calendar-light-mode tbody button,
          .calendar-light-mode button[aria-label*="day"],
          .calendar-light-mode button[aria-label*="Day"],
          .calendar-light-mode button[aria-label*="January"],
          .calendar-light-mode button[aria-label*="February"],
          .calendar-light-mode button[aria-label*="March"],
          .calendar-light-mode button[aria-label*="April"],
          .calendar-light-mode button[aria-label*="May"],
          .calendar-light-mode button[aria-label*="June"],
          .calendar-light-mode button[aria-label*="July"],
          .calendar-light-mode button[aria-label*="August"],
          .calendar-light-mode button[aria-label*="September"],
          .calendar-light-mode button[aria-label*="October"],
          .calendar-light-mode button[aria-label*="November"],
          .calendar-light-mode button[aria-label*="December"] {
            color: #1e293b !important;
          }
          
          /* Regular day buttons - not selected, not disabled, not outside */
          .calendar-light-mode button[class*="day"]:not([class*="day_selected"]):not([class*="day_disabled"]):not([class*="day_outside"]):not([aria-selected="true"]),
          .calendar-light-mode button:not([class*="day_selected"]):not([class*="day_disabled"]):not([class*="day_outside"]):not([aria-selected="true"]):not([class*="nav"]) {
            color: #1e293b !important;
            background-color: transparent !important;
          }
          
          /* Day buttons on hover */
          .calendar-light-mode button[class*="day"]:not([class*="day_disabled"]):not([class*="day_selected"]):not([aria-selected="true"]):hover,
          .calendar-light-mode button:not([class*="day_disabled"]):not([class*="day_selected"]):not([aria-selected="true"]):not([class*="nav"]):hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
          }
          
          /* Selected day - multiple selectors for maximum coverage */
          .calendar-light-mode button[class*="day_selected"],
          .calendar-light-mode button[aria-selected="true"],
          .calendar-light-mode button[aria-selected="true"][class*="day"],
          .calendar-light-mode button[aria-selected="true"][class*="rdp-day"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border-color: #2563eb !important;
          }
          
          /* Force background and text color for any selected button */
          .calendar-light-mode button[aria-selected="true"]:not([class*="nav"]),
          .calendar-light-mode button[class*="day_selected"]:not([class*="nav"]) {
            background-color: #2563eb !important;
            color: #ffffff !important;
          }
          
          .calendar-light-mode button[class*="day_selected"]:hover,
          .calendar-light-mode button[aria-selected="true"]:hover {
            background-color: #1d4ed8 !important;
            color: #ffffff !important;
          }
          
          /* Outside month days */
          .calendar-light-mode button[class*="day_outside"]:not([class*="day_selected"]):not([aria-selected="true"]),
          .calendar-light-mode button[class*="day-outside"]:not([class*="day_selected"]):not([aria-selected="true"]) {
            color: #94a3b8 !important;
          }
          
          /* Disabled days */
          .calendar-light-mode button[class*="day_disabled"],
          .calendar-light-mode button[disabled] {
            color: #cbd5e1 !important;
            opacity: 0.5 !important;
          }
          
          /* Today - not selected */
          .calendar-light-mode button[class*="day_today"]:not([class*="day_selected"]):not([aria-selected="true"]),
          .calendar-light-mode button[class*="day-today"]:not([class*="day_selected"]):not([aria-selected="true"]) {
            background-color: #f1f5f9 !important;
            color: #1e293b !important;
            font-weight: 600 !important;
          }
          
          /* Today AND selected - ensure white text on blue background */
          .calendar-light-mode button[class*="day_today"][class*="day_selected"],
          .calendar-light-mode button[class*="day_today"][aria-selected="true"],
          .calendar-light-mode button[class*="day-today"][class*="day_selected"],
          .calendar-light-mode button[class*="day-today"][aria-selected="true"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            font-weight: 600 !important;
          }
          
          /* Ensure selected date number is always visible */
          .calendar-light-mode button[aria-selected="true"] *,
          .calendar-light-mode button[class*="day_selected"] * {
            color: #ffffff !important;
          }
          
          /* Range start date - ensure text is visible */
          .calendar-light-mode button[class*="day-range-start"],
          .calendar-light-mode button[class*="range-start"],
          .calendar-light-mode button[class*="day_range_start"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border-color: #2563eb !important;
          }
          
          .calendar-light-mode button[class*="day-range-start"] *,
          .calendar-light-mode button[class*="range-start"] *,
          .calendar-light-mode button[class*="day_range_start"] * {
            color: #ffffff !important;
          }
          
          /* Range end date - ensure text is visible */
          .calendar-light-mode button[class*="day-range-end"],
          .calendar-light-mode button[class*="range-end"],
          .calendar-light-mode button[class*="day_range_end"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
          }
          
          .calendar-light-mode button[class*="day-range-end"] *,
          .calendar-light-mode button[class*="range-end"] *,
          .calendar-light-mode button[class*="day_range_end"] * {
            color: #ffffff !important;
          }
          
          /* Range middle dates */
          .calendar-light-mode button[class*="day-range-middle"],
          .calendar-light-mode button[class*="range-middle"],
          .calendar-light-mode button[class*="day_range_middle"] {
            background-color: #dbeafe !important;
            color: #1e293b !important;
          }
          
          /* Any button with a border that might be a selected date */
          .calendar-light-mode button[style*="border"],
          .calendar-light-mode button[class*="border"] {
            color: #1e293b !important;
          }
          
          /* Override for buttons with border AND selected state */
          .calendar-light-mode button[style*="border"][aria-selected="true"],
          .calendar-light-mode button[class*="border"][aria-selected="true"],
          .calendar-light-mode button[style*="border"][class*="day_selected"],
          .calendar-light-mode button[class*="border"][class*="day_selected"] {
            background-color: #2563eb !important;
            color: #ffffff !important;
          }
          
          .calendar-light-mode button[style*="border"][aria-selected="true"] *,
          .calendar-light-mode button[class*="border"][aria-selected="true"] *,
          .calendar-light-mode button[style*="border"][class*="day_selected"] *,
          .calendar-light-mode button[class*="border"][class*="day_selected"] * {
            color: #ffffff !important;
          }
          
          /* Head cells (day names) */
          .calendar-light-mode [class*="head_cell"],
          .calendar-light-mode th[class*="head_cell"],
          .calendar-light-mode th {
            color: #64748b !important;
            font-weight: 500 !important;
          }
          
          /* Caption label (month/year) */
          .calendar-light-mode [class*="caption_label"],
          .calendar-light-mode span[class*="caption_label"] {
            color: #1e293b !important;
            font-weight: 600 !important;
          }
          
          /* Navigation buttons - exclude from day button rules */
          .calendar-light-mode button[class*="nav_button"],
          .calendar-light-mode button[class*="nav-button"] {
            color: #475569 !important;
          }
          
          .calendar-light-mode button[class*="nav_button"]:hover,
          .calendar-light-mode button[class*="nav-button"]:hover {
            color: #1e293b !important;
            background-color: #f1f5f9 !important;
          }
          
          /* Override ALL possible muted/foreground colors */
          .calendar-light-mode button.text-muted-foreground,
          .calendar-light-mode button[class*="text-muted"],
          .calendar-light-mode button[class*="text-foreground"],
          .calendar-light-mode button[class*="accent-foreground"] {
            color: #1e293b !important;
          }
          
          /* Force text color on all buttons that are not navigation */
          .calendar-light-mode button:not([class*="nav"]):not([disabled]) {
            color: #1e293b !important;
          }
        `}</style>
      )}
      <DayPicker
        showOutsideDays={showOutsideDays}
        className={cn("p-3", isLight ? "calendar-light-mode" : "", className)}
        classNames={{
          months: "flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
          month: "space-y-4",
          caption: "flex justify-center pt-1 relative items-center",
          caption_label: cn(
            "text-sm font-medium",
            isLight ? "text-slate-900" : ""
          ),
          nav: "space-x-1 flex items-center",
          nav_button: cn(
            buttonVariants({ variant: "outline" }),
            "h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100",
            isLight ? "text-slate-600 hover:text-slate-900 hover:bg-slate-100" : ""
          ),
          nav_button_previous: "absolute left-1",
          nav_button_next: "absolute right-1",
          table: "w-full border-collapse space-y-1",
          head_row: "flex",
          head_cell: cn(
            "rounded-md w-9 font-normal text-[0.8rem]",
            isLight ? "text-slate-600" : "text-muted-foreground"
          ),
          row: "flex w-full mt-2",
          cell: "h-9 w-9 text-center text-sm p-0 relative [&:has([aria-selected].day-range-end)]:rounded-r-md [&:has([aria-selected].day-outside)]:bg-accent/50 [&:has([aria-selected])]:bg-accent first:[&:has([aria-selected])]:rounded-l-md last:[&:has([aria-selected])]:rounded-r-md focus-within:relative focus-within:z-20",
          day: cn(
            buttonVariants({ variant: "ghost" }),
            "h-9 w-9 p-0 font-normal aria-selected:opacity-100",
            isLight 
              ? "text-slate-900 hover:bg-slate-100 hover:text-slate-900 [&]:text-slate-900 [&]:!text-slate-900" 
              : ""
          ),
          day_range_end: "day-range-end",
          day_selected: cn(
            "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground",
            isLight ? "!bg-blue-600 !text-white hover:!bg-blue-700 !border-blue-600" : ""
          ),
          day_today: cn(
            "bg-accent text-accent-foreground",
            isLight ? "bg-slate-100 text-slate-900 font-semibold [&.day_selected]:bg-blue-600 [&.day_selected]:text-white [&[aria-selected='true']]:bg-blue-600 [&[aria-selected='true']]:text-white" : ""
          ),
          day_outside: cn(
            "day-outside text-muted-foreground aria-selected:bg-accent/50 aria-selected:text-muted-foreground",
            isLight ? "text-slate-400 aria-selected:text-slate-400" : ""
          ),
          day_disabled: cn(
            "text-muted-foreground opacity-50",
            isLight ? "text-slate-300" : ""
          ),
          day_range_middle: cn(
            "aria-selected:bg-accent aria-selected:text-accent-foreground",
            isLight ? "aria-selected:bg-blue-100 aria-selected:text-slate-900" : ""
          ),
          day_hidden: "invisible",
          ...classNames,
        }}
        components={{
          IconLeft: ({ className, ...props }) => (
            <ChevronLeft className={cn("h-4 w-4", className, isLight ? "text-slate-600" : "")} {...props} />
          ),
          IconRight: ({ className, ...props }) => (
            <ChevronRight className={cn("h-4 w-4", className, isLight ? "text-slate-600" : "")} {...props} />
          ),
        }}
        {...props}
      />
    </>
  )
}
Calendar.displayName = "Calendar"

export { Calendar }
