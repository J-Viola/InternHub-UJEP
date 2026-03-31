import React from "react";
import { FiBook, FiEdit, FiSearch, FiFilter, FiPlus, FiEye, FiEyeOff, FiSettings } from "react-icons/fi";
import { TbUsers } from "react-icons/tb";
import { RxCross1, RxCheck } from "react-icons/rx";
import { FaRegFileAlt, FaLock, FaUser, FaArrowLeft, FaSave, FaDownload, FaUpload, FaCalendarAlt, FaHeart, FaRegHeart } from "react-icons/fa";
import { FaLocationDot, FaFolderOpen, FaFileSignature, FaEnvelopeOpen, FaFileCircleCheck, FaCheck, FaAngleDown, FaAngleUp } from "react-icons/fa6";
import { MdOutlineManageAccounts, MdPersonOutline } from "react-icons/md";

const icons = {
    "angle-down": FaAngleDown,
    "angle-up": FaAngleUp,
    book: FiBook,
    edit: FiEdit,
    search: FiSearch,
    filter: FiFilter,
    plus: FiPlus,
    cross: RxCross1,
    check: RxCheck,
    users: TbUsers,
    user: MdPersonOutline,
    eye: FiEye,
    "eye-slash": FiEyeOff,
    lock: FaLock,
    download: FaDownload,
    gear: FiSettings,
    calendar: FaCalendarAlt,
    upload: FaUpload,
    save: FaSave,
    manage: MdOutlineManageAccounts,
    doc: FaRegFileAlt,
    heart: FaRegHeart,
    "heart-filled": FaHeart,
    "location-dot": FaLocationDot,
    "folder-open": FaFolderOpen,
    "file-signature": FaFileSignature,
    "envelope-open": FaEnvelopeOpen,
    "file-circle-check": FaFileCircleCheck,
    "arrow-left": FaArrowLeft,
};

export default function Icon({ name, size = 14, color = "text-current", property = "" }) {
    const IconComponent = icons[name];

    if (!IconComponent) {
        console.warn(`Icon "${name}" not found`);
        return null;
    }

    return <IconComponent size={size} className={`${color} ${property}`} />;
}
