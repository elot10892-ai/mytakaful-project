"""
AI Assistant module for MyTakaful application.
Provides helpful responses to user questions about the mutual system.
"""

import json
import os
from datetime import datetime
from i18n import t, get_current_language

class AIAssistant:
    """AI Assistant class for MyTakaful application."""
    
    def __init__(self):
        """Initialize the AI assistant."""
        self.knowledge_base = {
            'fr': {
                'mutual_explanation': "Le système de mutuelle MyTakaful est basé sur le principe de solidarité. Les membres cotisent régulièrement pour constituer un fonds commun qui permet d'aider ceux qui en ont besoin. Chaque contribution est répartie équitablement entre tous les membres actifs.",
                'group_choice': "Pour choisir un groupe, considérez vos besoins spécifiques. Les groupes peuvent être basés sur des professions, des intérêts communs ou des critères géographiques. Consultez les descriptions des groupes pour trouver celui qui correspond le mieux à vos attentes.",
                'contributions_explanation': "Les cotisations sont des paiements mensuels fixes de 10 MAD. Elles sont essentielles pour maintenir le fonds de la mutuelle et assurer l'aide aux membres en besoin. Vous pouvez payer vos cotisations via la section 'Paiement' de votre tableau de bord.",
                'pending_aid': "Une aide 'en attente' est une demande que vous avez soumise mais qui n'a pas encore été examinée par l'administration. L'équipe administrative vérifie les fonds disponibles et les critères avant d'approuver ou de rejeter votre demande.",
                'approved_aid': "Une aide 'approuvée' est une demande qui a été validée par l'administration. Les fonds seront transférés selon les modalités définies par la mutuelle.",
                'rejected_aid': "Une aide 'rejetée' est une demande qui n'a pas satisfait aux critères requis. Vous pouvez contacter l'administration pour plus d'informations sur les raisons du rejet.",
                'faq': {
                    'contribution_frequency': "Les cotisations sont mensuelles et doivent être payées avant le 5ème jour de chaque mois.",
                    'minimum_contribution_period': "Vous devez cotiser pendant au moins 3 mois consécutifs avant de pouvoir demander une aide.",
                    'maximum_aid_amount': "Le montant maximum d'une aide dépend des fonds disponibles dans votre groupe et est déterminé par l'administration.",
                    'aid_processing_time': "Les demandes d'aide sont généralement traitées dans un délai de 5 jours ouvrables."
                }
            },
            'en': {
                'mutual_explanation': "The MyTakaful mutual system is based on the principle of solidarity. Members contribute regularly to create a common fund that helps those in need. Each contribution is distributed fairly among all active members.",
                'group_choice': "To choose a group, consider your specific needs. Groups can be based on professions, common interests, or geographical criteria. Review group descriptions to find the one that best matches your expectations.",
                'contributions_explanation': "Contributions are fixed monthly payments of 10 MAD. They are essential to maintain the mutual fund and ensure assistance to members in need. You can pay your contributions via the 'Payment' section of your dashboard.",
                'pending_aid': "A 'pending' aid is a request you've submitted but hasn't been reviewed by administration yet. The administrative team checks available funds and criteria before approving or rejecting your request.",
                'approved_aid': "An 'approved' aid is a request that has been validated by administration. Funds will be transferred according to the terms defined by the mutual.",
                'rejected_aid': "A 'rejected' aid is a request that didn't meet the required criteria. You can contact administration for more information about the rejection reasons.",
                'faq': {
                    'contribution_frequency': "Contributions are monthly and must be paid before the 5th day of each month.",
                    'minimum_contribution_period': "You must contribute for at least 3 consecutive months before requesting aid.",
                    'maximum_aid_amount': "The maximum aid amount depends on funds available in your group and is determined by administration.",
                    'aid_processing_time': "Aid requests are typically processed within 5 business days."
                }
            },
            'ar': {
                'mutual_explanation': "يعتمد نظام التكافل MyTakaful على مبدأ التضامن. يساهم الأعضاء بانتظام في إنشاء صندوق مشترك يساعد المحتاجين. يتم توزيع كل مساهمة بشكل عادل بين جميع الأعضاء النشطين.",
                'group_choice': "لاختيار مجموعة، فكر في احتياجاتك الخاصة. يمكن أن تكون المجموعات مبنية على المهن أو الاهتمامات المشتركة أو المعايير الجغرافية. راجع أوصاف المجموعات للعثور على المجموعة التي تتوافق مع توقعاتك.",
                'contributions_explanation': "المساهمات هي مدفوعات شهرية ثابتة قدرها 10 دراهم. إنها ضرورية للحفاظ على صندوق التكافل وضمان المساعدة للأعضاء المحتاجين. يمكنك دفع مساهماتك عبر قسم 'الدفع' في لوحة التحكم الخاصة بك.",
                'pending_aid': "المساعدة 'المعلقة' هي طلب قدمته ولكن لم تتم مراجعته من قبل الإدارة. يتحقق الفريق الإداري من الأموال المتاحة والمعايير قبل الموافقة على طلبك أو رفضه.",
                'approved_aid': "المساعدة 'المعتمدة' هي طلب تم التحقق من صحته من قبل الإدارة. سيتم تحويل الأموال وفقًا للشروط المحددة بواسطة التكافل.",
                'rejected_aid': "المساعدة 'المرفوضة' هي طلب لم يستوفِ المعايير المطلوبة. يمكنك الاتصال بالإدارة للحصول على مزيد من المعلومات حول أسباب الرفض.",
                'faq': {
                    'contribution_frequency': "المساهمات شهرية ويجب دفعها قبل اليوم الخامس من كل شهر.",
                    'minimum_contribution_period': "يجب أن تساهم لمدة 3 أشهر متتالية على الأقل قبل طلب المساعدة.",
                    'maximum_aid_amount': "يعتمد الحد الأقصى لمبلغ المساعدة على الأموال المتاحة في مجموعتك ويحددها الإدارة.",
                    'aid_processing_time': "عادة ما تتم معالجة طلبات المساعدة خلال 5 أيام عمل."
                }
            }
        }
    
    def get_response(self, question, lang_code=None):
        """
        Get a response to a user question.
        
        Args:
            question (str): User question
            lang_code (str, optional): Language code
            
        Returns:
            str: AI-generated response
        """
        if lang_code is None:
            lang_code = get_current_language()
        
        # Normalize the question for matching
        normalized_question = question.lower().strip()
        
        # Get knowledge base for the language
        kb = self.knowledge_base.get(lang_code, self.knowledge_base['fr'])
        
        # Check for specific keywords in the question
        if any(keyword in normalized_question for keyword in ['mutuel', 'mutual', 'تكافل']):
            return kb['mutual_explanation']
        elif any(keyword in normalized_question for keyword in ['groupe', 'group', 'مجموعة']):
            return kb['group_choice']
        elif any(keyword in normalized_question for keyword in ['cotis', 'contribut', 'مساهم', 'مساهمة']):
            return kb['contributions_explanation']
        elif any(keyword in normalized_question for keyword in ['en attente', 'pending', 'معلق']):
            return kb['pending_aid']
        elif any(keyword in normalized_question for keyword in ['approuv', 'approv', 'معتمد']):
            return kb['approved_aid']
        elif any(keyword in normalized_question for keyword in ['rejet', 'reject', 'مرفوض']):
            return kb['rejected_aid']
        elif any(keyword in normalized_question for keyword in ['faq', 'question', 'سؤال']):
            # Handle FAQ questions
            if any(keyword in normalized_question for keyword in ['fréquenc', 'frequency', 'تكرار']):
                return kb['faq']['contribution_frequency']
            elif any(keyword in normalized_question for keyword in ['périod', 'period', 'فترة']):
                return kb['faq']['minimum_contribution_period']
            elif any(keyword in normalized_question for keyword in ['maximum', 'max', 'أقصى']):
                return kb['faq']['maximum_aid_amount']
            elif any(keyword in normalized_question for keyword in ['traitement', 'process', 'معالجة']):
                return kb['faq']['aid_processing_time']
        
        # Default response if no specific match
        default_responses = {
            'fr': "Je suis l'assistant MyTakaful. Je peux vous aider à comprendre le fonctionnement de la mutuelle, choisir un groupe, ou répondre à vos questions sur les cotisations et les aides. Posez-moi une question spécifique !",
            'en': "I'm the MyTakaful assistant. I can help you understand how the mutual works, choose a group, or answer your questions about contributions and aids. Ask me a specific question!",
            'ar': "أنا مساعد MyTakaful. يمكنني مساعدتك في فهم كيفية عمل التكافل، واختيار مجموعة، أو الإجابة عن أسئلتك حول المساهمات والمساعدات. اسألني سؤالاً محدداً!"
        }
        
        return default_responses.get(lang_code, default_responses['fr'])
    
    def get_suggestions(self, user_role='user', lang_code=None):
        """
        Get suggested questions based on user role.
        
        Args:
            user_role (str): User role ('user' or 'admin')
            lang_code (str, optional): Language code
            
        Returns:
            list: List of suggested questions
        """
        if lang_code is None:
            lang_code = get_current_language()
        
        suggestions = {
            'fr': [
                "Expliquez-moi le fonctionnement de la mutuelle",
                "Aidez-moi à choisir un groupe",
                "Expliquez-moi les cotisations",
                "Qu'est-ce qu'une aide 'en attente' ?"
            ],
            'en': [
                "Explain how the mutual works",
                "Help me choose a group",
                "Explain contributions",
                "What is a 'pending' aid?"
            ],
            'ar': [
                "اشرح لي كيف يعمل التكافل",
                "ساعدني في اختيار مجموعة",
                "اشرح المساهمات",
                "ما هي المساعدة 'المعلقة'؟"
            ]
        }
        
        return suggestions.get(lang_code, suggestions['fr'])

# Create a global instance of the AI assistant
ai_assistant = AIAssistant()